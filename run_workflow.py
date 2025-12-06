import sys
import json
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
        return f"{type_} {id_}"

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

    # define item/member
    def visitDefineStmt(self, ctx):
        # ctx is a statement context; child defineStmt() holds actual define
        if ctx.BOOK():
            item_type = "book"
            item_id = ctx.ITEM_ID().getText()
            k = state.key_item(item_type, item_id)
            state.items[k] = {}
            if ctx.fieldList():
                for f in ctx.fieldList().fieldAssign():
                    state.items[k][f.field().getText()] = self._evalValue(f.value())
            print(f"[DEFINE BOOK] {k}")

        elif ctx.MEMBER():
            member_id = ctx.MEMBER_ID().getText()
            state.members[member_id] = {}
            if ctx.fieldList():
                for f in ctx.fieldList().fieldAssign():
                    state.members[member_id][f.field().getText()] = self._evalValue(f.value())
            print(f"[DEFINE MEMBER] {member_id}")

    # txnStmt alternative labelled as txnStatement
    def visitTxnStmt(self, ctx):
        action = ctx.action().getText()
        t = ctx.target()

        actor = None
        if t.MEMBER_ID():
            actor = t.MEMBER_ID().getText()

        itype = "book"
        iid = t.ITEM_ID().getText()
        key = state.key_item(itype, iid)

        print(f"[TXN] {action.upper()} {key} by {actor}")

        # minimal effect (guard if item exists)
        if key in state.items:
            if action == "borrow":
                state.items[key]["status"] = "borrowed"
            elif action == "return":
                state.items[key]["status"] = "available"

    # update
    def visitUpdateStmt(self, ctx):
        t = ctx.target()

        # extract keys robustly (same logic as txn)
        itype = "book"
        iid = t.ITEM_ID().getText()
        key = state.key_item(itype, iid)

        print(f"[UPDATE] {key}")

        if key not in state.items:
            print(f"  [WARN] item not defined: {key} (skipping updates)")
            return None

        for f in ctx.fieldList().fieldAssign():
            field = f.field().getText()
            val = self._evalValue(f.value())
            state.items[key][field] = val
            print(f"   set {field} = {val}")

    # query
    def visitQueryStmt(self, ctx):
        print("[QUERY]")
        
        condtxt = None
        if ctx.whereClause():
            condtxt = ctx.whereClause().condition().getText()
            print("  where:", condtxt)

        for k, v in state.items.items():
            print("  item:", k, v)
                
    # if
    def visitIfStmt(self, ctx):
        cond = ctx.condition()
        text_form = cond.getText()
        result = self._evalCondition(cond)

        print(f"[IF] {text_form} -> {result}")
        if result:
            # then block: statement(0) is a list
            for s in ctx.thenBlock().statement():
                self.visit(s)
        else:
            if ctx.elseBlock():
                for s in ctx.elseBlock().statement():
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
    
    def _get_field_value(self, field_name):
        """
        field_name bisa 'book.status' atau hanya 'status'
        """
        if "." in field_name:
            type_, field = field_name.split(".")
        else:
            field = field_name

        for k, obj in state.items.items():
            if field in obj:
                return obj[field]
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

        left = self._get_field_value(field)

        if left is None:
            return False
        
        if op == "==": return left == val
        if op == "!=": return left != val
        if op == "<": return left < val
        if op == ">": return left > val
              
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
    print("Items:")
    print(json.dumps(state_out.items,indent=4))
    print("Members:")
    print(json.dumps(state_out.members,indent=4))

if __name__ == "__main__":
    run_dsl("workflow.kita")
