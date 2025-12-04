import sys
from antlr4 import *
from WorkflowLexer import WorkflowLexer
from WorkflowParser import WorkflowParser
from WorkflowVisitor import WorkflowVisitor

# -----------------------------
#   RUNTIME DATA STORE
# -----------------------------
class WorkflowState:
    def __init__(self):
        self.items = {}     # e.g. { "book B-123": {title:..., status:...} }
        self.members = {}   # e.g. { "A001": {...} }

    def key_item(self, type_, id_):
        if type_ is None or id_ is None:
            return None
        return f"{type_} {id_}"

    def key_member(self, id_):
        return id_

state = WorkflowState()


# -----------------------------
#   VISITOR IMPLEMENTATION
# -----------------------------
class ExecVisitor(WorkflowVisitor):
    # program : statement* EOF
    def visitProgram(self, ctx):
        for stmt in ctx.statement():
            # each stmt is a StatementContext (has child defineStmt/txnStmt/etc)
            self.visit(stmt)
        return state

    # txnStmt alternative labelled as txnStatement
    def visitTxnStatement(self, ctx):
        txn = ctx.txnStmt()
        action = txn.action().getText()
        t = txn.target()

        # Extract item_type and item_id robustly
        item_type = None
        item_id = None
        actor = None

        # target : ID ITEM_ID  | MEMBER_ID ARROW ID ITEM_ID
        if t.MEMBER_ID():
            actor = t.MEMBER_ID().getText()
            # when MEMBER_ID ARROW ID ITEM_ID, ID() exists (the item type)
            ids = t.ID()
            if ids:
                item_type = ids[0].getText()
            if t.ITEM_ID():
                item_id = t.ITEM_ID().getText()
        else:
            # direct form: ID ITEM_ID
            ids = t.ID()
            if ids:
                item_type = ids[0].getText()
            if t.ITEM_ID():
                item_id = t.ITEM_ID().getText()

        item_key = state.key_item(item_type, item_id)
        print(f"[TXN] {action.upper()} {item_key} by {actor}")

        # minimal effect (guard if item exists)
        if item_key and item_key in state.items:
            if action == "borrow":
                state.items[item_key]["status"] = "borrowed"
            elif action == "return":
                state.items[item_key]["status"] = "available"
        else:
            # if item missing, warn (do not crash)
            if item_key is None:
                print(f"  [WARN] txn target incomplete")
            else:
                print(f"  [WARN] item not defined: {item_key}")

        return None

    # define item/member
    def visitDefineStatement(self, ctx):
        # ctx is a statement context; child defineStmt() holds actual define
        defn = ctx.defineStmt()
        # memberDef : MEMBER_ID LBRACE ...
        if defn.itemDef():
            # itemDef was parsed as: ID ITEM_ID { fieldList? }
            # use ID() (parser-level) not ITEM_TYPE lexer token
            id_tokens = defn.itemDef().ID()
            item_type = id_tokens[0].getText() if id_tokens else None
            item_id = defn.itemDef().ITEM_ID().getText() if defn.itemDef().ITEM_ID() else None
            k = state.key_item(item_type, item_id)
            state.items[k] = {}
            fld = defn.itemDef().fieldList()
            if fld:
                for f in fld.fieldAssign():
                    key = f.field().getText()
                    val = self._evalValue(f.value())
                    state.items[k][key] = val
            print(f"[DEFINE ITEM] {k}")

        elif defn.memberDef():
            member_id = defn.memberDef().MEMBER_ID().getText() if defn.memberDef().MEMBER_ID() else None
            state.members[member_id] = {}
            fld = defn.memberDef().fieldList()
            if fld:
                for f in fld.fieldAssign():
                    key = f.field().getText()
                    val = self._evalValue(f.value())
                    state.members[member_id][key] = val
            print(f"[DEFINE MEMBER] {member_id}")

        return None

    # update
    def visitUpdateStatement(self, ctx):
        upd = ctx.updateStmt()
        t = upd.target()

        # extract keys robustly (same logic as txn)
        item_type = None
        item_id = None
        actor = None

        if t.MEMBER_ID():
            actor = t.MEMBER_ID().getText()
            ids = t.ID()
            if ids:
                item_type = ids[0].getText()
            if t.ITEM_ID():
                item_id = t.ITEM_ID().getText()
        else:
            ids = t.ID()
            if ids:
                item_type = ids[0].getText()
            if t.ITEM_ID():
                item_id = t.ITEM_ID().getText()

        key = state.key_item(item_type, item_id)
        print(f"[UPDATE] {key}")

        if key not in state.items:
            print(f"  [WARN] item not defined: {key} (skipping updates)")
            return None

        fldlist = upd.fieldList()
        if fldlist:
            for f in fldlist.fieldAssign():
                field = f.field().getText()
                val = self._evalValue(f.value())
                state.items[key][field] = val
                print(f"   set {field} = {val}")

        return None

    # query
    def visitQueryStatement(self, ctx):
        print("[QUERY]")
        q = ctx.queryStmt()
        sel = q.selectClause().selectFields().getText() if q.selectClause() else "*"
        where = q.whereClause().condition().getText() if q.whereClause() else None
        print(f"  select: {sel}")
        print(f"  where : {where}")
        # naive evaluator: print matching items if where is simple "type.field == value"
        if where:
            # very naive parsing: split on spaces (sufficient for simple cases)
            parts = where.split()
            if len(parts) >= 3:
                left = parts[0]
                op = parts[1]
                right = parts[2].strip('"')
                for k, props in state.items.items():
                    if '.' in left:
                        tname, fname = left.split('.', 1)
                        if props.get('_type') == tname or True:  # we don't store _type reliably here; just check field
                            if fname in props:
                                val = props[fname]
                                ok = (op == '==' and str(val) == right) or (op == '!=' and str(val) != right)
                                if ok:
                                    print(f"  match: {k}: {props}")
        else:
            for item_key, fields in state.items.items():
                print(f"  - {item_key}: {fields}")
        return None

    # if
    def visitIfStatement(self, ctx):
        if_ctx = ctx.ifStmt()
        cond_ctx = if_ctx.condition()
        cond = self._evalCondition(cond_ctx)
        print(f"[IF] condition -> {cond}")
        if cond:
            # then block: statement(0) is a list
            for s in if_ctx.statement(0):
                self.visit(s)
        else:
            if if_ctx.ELSE():
                for s in if_ctx.statement(1):
                    self.visit(s)
        return None

    # -----------------------------
    # Helpers
    # -----------------------------
    def _evalValue(self, v):
        if v is None:
            return None
        if v.STRING():
            return v.STRING().getText().strip('"')
        if v.NUMBER():
            n = v.NUMBER().getText()
            return float(n) if '.' in n else int(n)
        if v.DATE():
            return v.DATE().getText().strip('"')
        if v.TRUE(): 
            return True
        if v.FALSE(): 
            return False
        return None

    def _evalCondition(self, c):
        # defensive: ensure c and expression exist
        if c is None or len(c.expression()) == 0:
            return False
        expr = c.expression(0)
        if expr is None or expr.field() is None or expr.COMPARISON() is None or expr.value() is None:
            return False
        field = expr.field().getText()
        op = expr.COMPARISON().getText()
        val = self._evalValue(expr.value())

        # lookup field in any item
        for k, f in state.items.items():
            # field may be dotted like book.status or just status
            if '.' in field:
                # prefer match on suffix name
                parts = field.split('.', 1)
                fname = parts[1]
            else:
                fname = field
            if fname in f:
                left = f[fname]
                if op == "==": return left == val
                if op == "!=": return left != val
                try:
                    if op == "<": return left < val
                    if op == ">": return left > val
                except Exception:
                    return False
        return False


# -----------------------------
# ENTRYPOINT
# -----------------------------
def run_dsl(filename):
    print("Running DSL:", filename)
    input_stream = FileStream(filename, encoding="utf-8")
    lexer = WorkflowLexer(input_stream)

    # optional: remove default console errors (keep them if you want raw ANTLR messages)
    # lexer.removeErrorListeners()

    token_stream = CommonTokenStream(lexer)
    parser = WorkflowParser(token_stream)

    # parser.removeErrorListeners()
    # parser.addErrorListener(YourCustomErrorListener())  # optional

    tree = parser.program()

    visitor = ExecVisitor()
    state_out = visitor.visit(tree)

    print("\nFinal State:")
    print("Items:", state_out.items)
    print("Members:", state_out.members)


if __name__ == "__main__":
    run_dsl("workflow.kita")
