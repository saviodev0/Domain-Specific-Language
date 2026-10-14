lexer grammar TankScriptLexer;

TANK       : 'tank';
SUBMARINE  : 'submarine';
GUN        : 'gun';
TORPEDO    : 'torpedo';
TEAM       : 'team';
BATTLE     : 'battle';
MOVE       : 'move';
ATTACK     : 'attack';
FIRE       : 'fire';
DIVE       : 'dive';
SURFACE    : 'surface';
IF         : 'if';
VS         : 'vs';
REPEAT     : 'repeat';
SONAR      : 'sonar';

IDENTIFIER : [a-zA-Z_] [a-zA-Z_0-9]*;
MALFORMED_NUMBER : [0-9]+ '.' [0-9]* '.' [0-9.]*;
FLOAT      : [0-9]+ '.' [0-9]+;
NUMBER     : [0-9]+;
STRING     : '"' ('\\' ~[\r\n] | ~["\\\r\n])* '"'
           | '\'' ('\\' ~[\r\n] | ~['\\\r\n])* '\'';

LBRACE     : '{';
RBRACE     : '}';
DOT        : '.';
LESS       : '<';
GREATER    : '>';
EQ         : '==';
PLUS       : '+';
MINUS      : '-';

COMMENT    : '#' ~[\r\n]* -> skip;
WHITESPACE : [ \t\r\n]+ -> skip;