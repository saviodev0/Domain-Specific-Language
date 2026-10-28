parser grammar TankScriptParser;

options { tokenVocab = TankScriptLexer; }

programa    : (declaracao | instrucao)* EOF ;

declaracao  : unidade | equipe | batalha ;
unidade     : (TANK | SUBMARINE) IDENTIFIER LBRACE (propriedade | arma)* RBRACE ;
arma        : (GUN | TORPEDO) IDENTIFIER LBRACE propriedade* RBRACE ;
propriedade : IDENTIFIER numero ;
equipe      : TEAM IDENTIFIER LBRACE IDENTIFIER* RBRACE ;
batalha     : BATTLE IDENTIFIER LBRACE IDENTIFIER VS IDENTIFIER RBRACE ;

instrucao   : movimento | ataque | disparo | mergulho | emersao
            | sonar | condicional | repeticao ;
movimento   : MOVE IDENTIFIER numero numero ;
ataque      : ATTACK IDENTIFIER IDENTIFIER ;
disparo     : FIRE IDENTIFIER IDENTIFIER IDENTIFIER ;
mergulho    : DIVE IDENTIFIER numero ;
emersao     : SURFACE IDENTIFIER ;
sonar       : SONAR IDENTIFIER ;
condicional : IF comparacao bloco ;
repeticao   : REPEAT NUMBER bloco ;
bloco       : LBRACE instrucao* RBRACE ;

comparacao  : primario (LESS | GREATER | EQ) primario ;
primario    : numero | STRING | IDENTIFIER (DOT IDENTIFIER)? ;
numero      : NUMBER | FLOAT ;
