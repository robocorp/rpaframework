import pytest
from RPA.core.geometry import Undefined
from RPA.core.locators import PointLocator, OffsetLocator, ImageLocator
from RPA.core.locators.syntax import (
    Chain,
    Expression,
    InvalidSyntax,
    Not,
    Resolver,
    SyntaxParser,
    Token,
    Tokenizer,
    TokenPair,
)


TOKENIZED = {
    "(point:10,20 or point:20,20) then offset:200,0": [
        TokenPair(Token.LPAREN, "("),
        TokenPair(Token.LOCATOR, PointLocator(10, 20)),
        TokenPair(Token.OR, "or"),
        TokenPair(Token.LOCATOR, PointLocator(20, 20)),
        TokenPair(Token.RPAREN, ")"),
        TokenPair(Token.THEN, "then"),
        TokenPair(Token.LOCATOR, OffsetLocator(200, 0)),
    ],
    "(point:10,20 || point:20,20) + offset:200,0": [
        TokenPair(Token.LPAREN, "("),
        TokenPair(Token.LOCATOR, PointLocator(10, 20)),
        TokenPair(Token.OR, "||"),
        TokenPair(Token.LOCATOR, PointLocator(20, 20)),
        TokenPair(Token.RPAREN, ")"),
        TokenPair(Token.THEN, "+"),
        TokenPair(Token.LOCATOR, OffsetLocator(200, 0)),
    ],
    "!point:200,200 and point:10,10 and not image:some_image.png": [
        TokenPair(Token.NOT, "!"),
        TokenPair(Token.LOCATOR, PointLocator(200, 200)),
        TokenPair(Token.AND, "and"),
        TokenPair(Token.LOCATOR, PointLocator(10, 10)),
        TokenPair(Token.AND, "and"),
        TokenPair(Token.NOT, "not"),
        TokenPair(Token.LOCATOR, ImageLocator("some_image.png")),
    ],
    "!!!!!point:200,200": [
        TokenPair(Token.NOT, "!"),
        TokenPair(Token.NOT, "!"),
        TokenPair(Token.NOT, "!"),
        TokenPair(Token.NOT, "!"),
        TokenPair(Token.NOT, "!"),
        TokenPair(Token.LOCATOR, PointLocator(200, 200)),
    ],
    "(((point:200,200)))": [
        TokenPair(Token.LPAREN, "("),
        TokenPair(Token.LPAREN, "("),
        TokenPair(Token.LPAREN, "("),
        TokenPair(Token.LOCATOR, PointLocator(200, 200)),
        TokenPair(Token.RPAREN, ")"),
        TokenPair(Token.RPAREN, ")"),
        TokenPair(Token.RPAREN, ")"),
    ],
}


@pytest.mark.parametrize("text, tokens", TOKENIZED.items())
def test_tokenizer(text, tokens):
    assert Tokenizer.tokenize(text) == tokens


PARSED = {
    "(point:10,20 or point:20,20) then offset:200,0": Chain(
        Expression(PointLocator(x=10, y=20), Token.OR, PointLocator(x=20, y=20)),
        OffsetLocator(x=200, y=0),
    ),
    "!point:200,200 and point:10,10 and not image:some_image.png": Expression(
        Expression(Not(PointLocator(200, 200)), Token.AND, PointLocator(10, 10)),
        Token.AND,
        Not(ImageLocator("some_image.png")),
    ),
    "!!!!!point:200,200": Not(Not(Not(Not(Not(PointLocator(200, 200)))))),
    "(((point:200,200)))": PointLocator(200, 200),
    "not (point:1,1 or point:2,2) then (point:3,3 and point:4,4)": Chain(
        Not(Expression(PointLocator(1, 1), Token.OR, PointLocator(2, 2))),
        Expression(PointLocator(3, 3), Token.AND, PointLocator(4, 4)),
    ),
    "(image:logo.png then offset:100,0) or (image:hamburger.png then offset:200,200)": Expression(
        Chain(
            ImageLocator("logo.png"),
            OffsetLocator(100, 0),
        ),
        Token.OR,
        Chain(
            ImageLocator("hamburger.png"),
            OffsetLocator(200, 200),
        ),
    ),
}


@pytest.mark.parametrize("text, expression", PARSED.items())
def test_parser(text, expression):
    assert SyntaxParser().parse(text) == expression


def test_resolver():
    def finder(base, locator):
        return [f"{base} -> {locator}"]

    resolver = Resolver(finder)
    result = resolver.dispatch(
        "(point:10,20 or point:20,20) then offset:200,0 then "
        "(image:test.png and image:logo.png or point:200,200)"
    )

    assert result == [
        "Undefined() -> PointLocator(x=10, y=20) -> OffsetLocator(x=200, y=0) -> ImageLocator(path='logo.png', confidence=None, source=None)",
        "Undefined() -> PointLocator(x=10, y=20) -> OffsetLocator(x=200, y=0) -> ImageLocator(path='test.png', confidence=None, source=None)",
    ]


def test_resolver_not():
    def finder(base, locator):
        if isinstance(locator, PointLocator):
            return ["somevalue"]
        if isinstance(locator, ImageLocator):
            return []

    resolver = Resolver(finder)
    result = resolver.dispatch("not (point:10,10 and image:notexist.png)")

    assert result == [Undefined()]
