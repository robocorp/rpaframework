import pytest
from RPA.core.geometry import Undefined
from RPA.core.locators import (
    literal,
    LocatorsDatabase,
    PointLocator,
    OffsetLocator,
    ImageLocator,
    OcrLocator,
    BrowserLocator,
)
from RPA.core.locators.syntax import (
    Peekable,
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


class TestTokenizer:
    ALIASES = {
        "SimpleAlias": ImageLocator("simple.png"),
        "Dotted.Alias": ImageLocator("dotted.png"),
        "Spaced Alias": ImageLocator("spaced.png"),
    }

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
        "SimpleAlias": [TokenPair(Token.LOCATOR, ImageLocator("simple.png"))],
        "Dotted.Alias": [TokenPair(Token.LOCATOR, ImageLocator("dotted.png"))],
        '"Spaced Alias"': [TokenPair(Token.LOCATOR, ImageLocator("spaced.png"))],
        'ocr:"New File"': [TokenPair(Token.LOCATOR, OcrLocator("New File"))],
        'point:"200","300"': [TokenPair(Token.LOCATOR, PointLocator(200, 300))],
        '(point:10,20 & (ocr:"Cool  ) Stuff"))': [
            TokenPair(Token.LPAREN, "("),
            TokenPair(Token.LOCATOR, PointLocator(10, 20)),
            TokenPair(Token.AND, "&"),
            TokenPair(Token.LPAREN, "("),
            TokenPair(Token.LOCATOR, OcrLocator("Cool  ) Stuff")),
            TokenPair(Token.RPAREN, ")"),
            TokenPair(Token.RPAREN, ")"),
        ],
        'browser:"spaced argument","second spaced argument"': [
            TokenPair(
                Token.LOCATOR,
                BrowserLocator("spaced argument", "second spaced argument"),
            )
        ],
    }

    @pytest.mark.parametrize("text, tokens", TOKENIZED.items())
    def test_tokenizer(self, monkeypatch, text, tokens):
        monkeypatch.setattr(
            LocatorsDatabase, "load_by_name", lambda name, _: self.ALIASES[name]
        )
        assert Tokenizer.tokenize(text, literal.parse) == tokens


class TestParser:
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
    def test_parser(self, text, expression):
        assert SyntaxParser().parse(text, literal.parse) == expression


class TestResolver:
    def test_dispatch(self):
        def finder(base, locator):
            return [f"{base} -> {locator}"]

        resolver = Resolver(finder)
        result = resolver.dispatch(
            "(point:10,20 or point:20,20) then offset:200,0 then "
            "(image:test.png and image:logo.png or point:200,200)"
        )

        assert result == [
            "undefined -> point:10,20 -> offset:200,0 -> image:logo.png",
            "undefined -> point:10,20 -> offset:200,0 -> image:test.png",
        ]

    def test_negate_empty(self):
        def finder(base, locator):
            if isinstance(locator, PointLocator):
                return ["somevalue"]
            if isinstance(locator, ImageLocator):
                return []

        resolver = Resolver(finder)
        result = resolver.dispatch("not (point:10,10 and image:notexist.png)")

        assert result == [Undefined()]


class TestPeekable:
    def test_peek_first(self):
        pk = Peekable([1, 2, 3])

        assert pk.peek == 1
        assert pk.current == Peekable.EOF
        assert not pk.is_empty

    def test_peek_next(self):
        pk = Peekable([1, 2, 3])
        first = next(pk)

        assert first == 1
        assert pk.current == 1
        assert pk.peek == 2
        assert not pk.is_empty

    def test_peek_last(self):
        pk = Peekable([1, 2, 3])
        next(pk)
        next(pk)
        next(pk)

        assert pk.current == 3
        assert pk.peek == Peekable.EOF
        assert pk.is_empty

    def test_exhaust(self):
        pk = Peekable([1, 2, 3])
        next(pk)
        next(pk)
        next(pk)

        with pytest.raises(StopIteration):
            next(pk)
