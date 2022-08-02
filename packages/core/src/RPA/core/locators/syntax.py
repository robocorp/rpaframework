import re
from enum import Enum
from typing import Callable, List, NamedTuple, Optional, Union

from RPA.core.geometry import Point, Region, Undefined
from RPA.core.locators import literal, Locator


Geometry = Union[Point, Region, Undefined]


class InvalidSyntax(ValueError):
    """Raised when given syntax is malformed."""


class Token(Enum):
    """Possible tokens in a locator."""

    THEN = "then"
    AND = "and"
    OR = "or"
    NOT = "not"
    LPAREN = "left parenthesis"
    RPAREN = "right parenthesis"
    LOCATOR = "locator"


ValueType = Union[Locator, "Not", "Expression", "Chain"]


class TokenPair(NamedTuple):
    """Pair of resolved token and original value."""

    token: Token
    value: Union[str, Locator]


class Not(NamedTuple):
    """Negated value."""

    value: ValueType

    def __repr__(self):
        return f"Not({self.value})"


class Expression(NamedTuple):
    """A conditional expression between two values."""

    lhs: ValueType
    op: Token
    rhs: ValueType

    def __repr__(self):
        return f"Expression({self.lhs} {self.op.value} {self.rhs})"


class Chain(tuple):
    """A set of consecutive values."""

    def __new__(cls, *args):
        return super().__new__(cls, args)

    def __repr__(self):
        return f"Chain({', '.join(str(val) for val in self)})"


class Peekable:
    """Generator-like wrapper with the ability
    to inspect the next value without consuming it.
    """

    EOF = object()

    def __init__(self, iterable):
        self._iterable = iter(iterable)
        self._current = self.EOF
        self._peek = self.EOF
        self._next()

    def __iter__(self):
        return self

    def __next__(self):
        if self.is_empty:
            raise StopIteration

        self._next()
        return self._current

    @property
    def current(self):
        return self._current

    @property
    def peek(self):
        return self._peek

    @property
    def is_empty(self):
        return self._peek is self.EOF

    def _next(self):
        self._current = self._peek
        try:
            self._peek = next(self._iterable)
        except StopIteration:
            self._peek = self.EOF


class Tokenizer:
    """Methods for tokenizing a locator string."""

    # fmt: off
    TOKEN_PATTERNS = [
        r"(?P<THEN>then|\+)",
        r"(?P<AND>and|\&\&|\&)",
        r"(?P<OR>or|\|\||\|)",
        r"(?P<NOT>not|\!)",
        r"(?P<LPAREN>\()",
        r"(?P<RPAREN>\))",
        (
            r"(?P<LOCATOR>"
            r"(\w+\:)?"      # Optional locator typename, e.g. ocr:
            r"(("            # Argument definition:
            r"\"[^\"]*\""    # 1. If quoted, continue until end quote
            r"|"             # or
            r"[^\s\)]+"      # 2. If unquoted, continue until whitespace or paren
            r")[\,]?)+"      # One or more arguments, comma delimited
            r")"
        ),
        r"(?P<SKIP>\s+)",
        r"(?P<MISMATCH>.+)",
    ]
    # fmt: on

    PATTERN = re.compile("|".join(TOKEN_PATTERNS))

    @classmethod
    def tokenize(
        cls, locator: str, parser: Callable[[str], Locator]
    ) -> List[TokenPair]:
        """Convert locator string to list of token pairs."""
        scanner = cls.PATTERN.scanner(locator)

        tokens = []
        for match in iter(scanner.match, None):
            name = match.lastgroup
            value = match.group()

            if name == "MISMATCH":
                raise InvalidSyntax(f"Unknown token: '{value}'")

            if name == "SKIP":
                continue

            if name == "LOCATOR":
                value = parser(value)

            pair = TokenPair(Token[name], value)
            tokens.append(pair)

        if not tokens:
            raise InvalidSyntax("Empty expression")

        return tokens


class SyntaxParser:
    """Methods for parsing a locator string into a tree."""

    def __init__(self):
        self.tokens = Peekable([])

    def parse(self, locator: str, parser: Callable[[str], Locator]) -> ValueType:
        """Parse locator string to tokenized expression."""
        pairs = Tokenizer.tokenize(locator, parser)
        self.tokens = Peekable(pairs)
        return self._chain()

    def _chain(self) -> ValueType:
        """Chain of expressions."""
        links = [self._expression()]
        while self._accept(Token.THEN):
            links.append(self._expression())

        if len(links) == 1:
            return links[0]

        return Chain(*links)

    def _expression(self) -> ValueType:
        """Either a single value or expression between two values."""
        expr = self._value()
        while self._accept(Token.AND) or self._accept(Token.OR):
            op = self.tokens.current
            rhs = self._value()
            expr = Expression(expr, op.token, rhs)

        return expr

    def _value(self) -> ValueType:
        """Either a locator literal or nested expression inside parentheses."""
        if self._accept(Token.NOT):
            return Not(self._value())
        elif self._accept(Token.LOCATOR):
            return self.tokens.current.value
        elif self._accept(Token.LPAREN):
            chain = self._chain()
            self._expect(Token.RPAREN)
            return chain
        else:
            raise InvalidSyntax("Expected locator or parentheses")

    def _consume(self) -> TokenPair:
        """Step forward to the next token and return the current one."""
        try:
            return next(self.tokens)
        except StopIteration:
            # pylint: disable=raise-missing-from
            raise InvalidSyntax("Unexpected end of expression")

    def _accept(self, token: Token) -> bool:
        """Consume tokens if the next one matches."""
        if not self.tokens.is_empty and self.tokens.peek.token == token:
            self._consume()
            return True
        else:
            return False

    def _expect(self, token: Token):
        """Assert that the next token is as expected."""
        if self.tokens.is_empty:
            raise InvalidSyntax("Unexpected end of expression")

        if not self._accept(token):
            actual = self.tokens.peek.token
            raise InvalidSyntax(f"Expected '{token.value}', was '{actual.value}'")


class Resolver:
    """Parser for locator expressions and resolving them into a set of final values."""

    def __init__(self, finder, database: Optional[str] = None):
        self.finder = finder
        self.database = database
        self._stack = [Undefined()]

    @property
    def current(self):
        return self._stack[-1]

    def dispatch(self, locator: str):
        """Visit locator tree."""

        def from_literal(value: str) -> Locator:
            return literal.parse(value, self.database)

        root = SyntaxParser().parse(locator=locator, parser=from_literal)
        return sorted(self._resolve(root))

    def _resolve(self, value: Union[ValueType, bool]):
        """Resolve value of any type."""
        resolvers = {
            Locator: self._locator,
            Not: self._not,
            Expression: self._expression,
            Chain: self._chain,
        }

        for type_, func in resolvers.items():
            if isinstance(value, type_):
                return func(value)

        raise RuntimeError(f"Unexpected value: {value}")

    def _chain(self, chain: Chain):
        """Resolve chain of expressions."""
        current = self._resolve(chain[0])

        for link in chain[1:]:
            temp = []
            for base in current:
                self._stack.append(base)
                try:
                    value = self._resolve(link)
                    if not value:
                        continue
                    temp.extend(value)
                finally:
                    self._stack.pop()

            current = []
            for value in temp:
                if value not in current:
                    current.append(value)

        return current

    def _expression(self, expr: Expression):
        """Resolve conditional expression."""
        if expr.op == Token.OR:
            lhs = self._resolve(expr.lhs)
            if lhs:
                return lhs
            rhs = self._resolve(expr.rhs)
            if rhs:
                return rhs
            return []

        elif expr.op == Token.AND:
            lhs = self._resolve(expr.lhs)
            if not lhs:
                return []
            rhs = self._resolve(expr.rhs)
            if not rhs:
                return []
            return lhs + rhs

        else:
            raise RuntimeError(f"Unexpected expression: {expr}")

    def _locator(self, locator: Locator):
        """Resolve final values for locator."""
        return self.finder(self.current, locator)

    def _not(self, negated: Not):
        """Negate resolved values."""
        value = self._resolve(negated.value)
        if not value:
            return [Undefined()]
        else:
            return []
