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
    : ID ITEM_ID                // use ID (type name) + ITEM_ID
    | MEMBER_ID ARROW ID ITEM_ID
    ;

defineStmt
    : DEFINE ID ITEM_ID LBRACE fieldList? RBRACE   // define book B-123 {..}
    | DEFINE MEMBER_ID LBRACE fieldList? RBRACE    // define A001 {..}
    ;

updateStmt : UPDATE target SET fieldList ;

queryStmt : QUERY (selectClause)? whereClause? ;

selectClause : SELECT selectFields ;
selectFields : STAR | field (COMMA field)* ;
whereClause : WHERE condition ;

ifStmt : IF condition THEN LBRACE statement* RBRACE (ELSE LBRACE statement* RBRACE)? ;

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

TRUE        : 'true';
FALSE       : 'false';

// specific tokens BEFORE ID
ITEM_ID     : [A-Z][A-Z0-9\-]* ;  // B-123
MEMBER_ID   : 'A' [0-9]+ ;   // contoh A001, A123
COMPARISON  : '==' | '!=' | '<=' | '>=' | '<' | '>';
LOGICAL_OP  : 'and' | 'or';

// literals
DATE   : '"' [0-9]{4} '-' [0-9]{2} '-' [0-9]{2} '"' ; // "YYYY-MM-DD"
STRING : '"' (~["\\] | '\\' .)* '"' ;
NUMBER : [0-9]+ ('.' [0-9]+)? ;

// now the single ID token for names (item types, fields)
ID : [a-zA-Z_][a-zA-Z0-9_]* ;

// parser-level field rule
field : ID ('.' ID)* ;

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
