grammar Workflow;

program : statement* EOF ;

statement
    : txnStmt SEMICOLON
    | defineStmt SEMICOLON
    | updateStmt SEMICOLON
    | queryStmt SEMICOLON
    | ifStmt
    ;

txnStmt : action target (WITH paramList)? ;

action : BORROW | RETURN | RESERVE | EXTEND | MARK_LOST ;

target
    : BOOK ITEM_ID                          // book B-123
    | MEMBER MEMBER_ID ARROW BOOK ITEM_ID   // member A001 -> book B-123  
    | MEMBER_ID ARROW BOOK ITEM_ID          // A001 -> book B-123
    ;

defineStmt
    : DEFINE BOOK ITEM_ID LBRACE fieldList? RBRACE   // define book B-123 {..}
    | DEFINE MEMBER MEMBER_ID LBRACE fieldList? RBRACE    // define member A001 {..}
    ;

updateStmt : UPDATE target SET fieldList ;

queryStmt : QUERY (selectClause)? whereClause? ;

selectClause : SELECT selectFields ;
selectFields : STAR | field (COMMA field)* ;
whereClause : WHERE condition ;

ifStmt : IF condition THEN thenBlock (ELSE elseBlock)? ;

thenBlock : LBRACE statement* RBRACE ;
elseBlock : LBRACE statement* RBRACE ;

condition : expression (LOGICAL_OP expression)* ;
expression : field COMPARISON value | LPAREN condition RPAREN ;

fieldList : fieldAssign (COMMA fieldAssign)* ;
fieldAssign : field EQ value ;
paramList : paramAssign (COMMA paramAssign)* ;
paramAssign : ID EQ value ;

// LEXER (keywords first)
BORROW      : 'borrow';
RETURN      : 'return';
RESERVE     : 'reserve';
EXTEND      : 'extend';
MARK_LOST   : 'mark_lost' | 'lost';
DEFINE      : 'define';
UPDATE      : 'update';
QUERY       : 'query';
SELECT      : 'select';
WHERE       : 'where';
IF          : 'if';
THEN        : 'then';
ELSE        : 'else';
WITH        : 'with';
SET         : 'set';
BOOK        : 'book';
MEMBER      : 'member';

TRUE        : 'true';
FALSE       : 'false';

// specific tokens BEFORE ID
MEMBER_ID   : 'A' [0-9]+ ;   // contoh A001, A123
ITEM_ID     : [A-Z][A-Z0-9\-]* ;  // B-123
COMPARISON  : '==' | '!=' | '<=' | '>=' | '<' | '>';
LOGICAL_OP  : 'and' | 'or';

// literals
DATE   : '"' [0-9]{4} '-' [0-9]{2} '-' [0-9]{2} '"' ; // "YYYY-MM-DD"
STRING : '"' (~["\\] | '\\' .)* '"' ;
NUMBER : [0-9]+ ('.' [0-9]+)? ;

// now the single ID token for names (item types, fields)
ID : [a-zA-Z_][a-zA-Z0-9_]* ;

// parser-level field rule
field : (ID | BOOK | MEMBER) ('.' ID)* ;

// values
value : STRING | NUMBER | DATE | TRUE | FALSE ;

// comments & whitespace
COMMENT : '/*' .*? '*/' -> channel(HIDDEN) ;
COMMENT_LINE : '//' ~[\r\n]* -> channel(HIDDEN) ;
WS : [ \t\r\n]+ -> skip ;

// symbols
SEMICOLON : ';' ;
COMMA : ',' ;
LPAREN : '(' ;
RPAREN : ')' ;
LBRACE : '{' ;
RBRACE : '}' ;
ARROW : '->' ;
EQ : '=' ;
STAR : '*' ;
