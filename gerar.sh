#!/usr/bin/env sh
set -eu

export ANTLR4_TOOLS_ANTLR_VERSION=4.13.2
antlr4 -Dlanguage=Python3 -visitor -Xexact-output-dir -o gerado tankscript/TankScriptLexer.g4