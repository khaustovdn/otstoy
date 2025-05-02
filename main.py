import re
import sys
import logging
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Generic,
)
from dataclasses import dataclass
from enum import Enum, auto
from abc import abstractmethod

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import (
    QAction,
    QFont,
    QKeySequence,
    QPalette,
    QColor
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QHeaderView,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)


class DarkTheme:

    _CATPPUCCIN_PALETTE = {
        "base": "#1e1e2e",
        "text": "#cdd6f4",
        "disabled_text": "#6c7086",
        "highlight": "#89b4fa",
        "highlight_text": "#1e1e2e",
        "alternate_base": "#313244",
        "tooltip_base": "#585b70",
        "button": "#313244",
        "button_text": "#cdd6f4",
        "bright_text": "#f38ba8",
        "surface1": "#45475a",
        "overlay0": "#6c7086",
        "current_line": "#313244",
    }

    _BASE_FONT_SIZE = 14
    _TABLET_FONT_SIZE = 16
    _TABLET_DIAGONAL_INCH = 9

    @classmethod
    def get_color(cls, color_name: str) -> str:
        return cls._CATPPUCCIN_PALETTE.get(color_name, "#000000")

    @classmethod
    def apply_theme(cls, app: QApplication) -> None:
        palette = app.palette()
        colors = cls._CATPPUCCIN_PALETTE

        role_mappings = {
            QPalette.ColorRole.Window: colors["base"],
            QPalette.ColorRole.WindowText: colors["text"],
            QPalette.ColorRole.Base: colors["base"],
            QPalette.ColorRole.AlternateBase: colors["alternate_base"],
            QPalette.ColorRole.ToolTipBase: colors["tooltip_base"],
            QPalette.ColorRole.ToolTipText: colors["text"],
            QPalette.ColorRole.Text: colors["text"],
            QPalette.ColorRole.Button: colors["button"],
            QPalette.ColorRole.ButtonText: colors["button_text"],
            QPalette.ColorRole.BrightText: colors["bright_text"],
            QPalette.ColorRole.Highlight: colors["highlight"],
            QPalette.ColorRole.HighlightedText: colors["highlight_text"],
        }

        for role, color in role_mappings.items():
            palette.setColor(role, QColor(color))

        app.setPalette(palette)
        cls._apply_stylesheet(app)
        cls.apply_adaptive_styles(app)

    @classmethod
    def _apply_stylesheet(cls, app: QApplication) -> None:
        colors = cls._CATPPUCCIN_PALETTE
        stylesheet = f"""
            /* Global Styles */
            QWidget {{
                font-family: "Inter", "Segoe UI", system-ui;
                font-size: {cls._BASE_FONT_SIZE}px;
                color: {colors['text']};
                background: {colors['base']};
            }}

            /* Text Editors */
            QTextEdit, QPlainTextEdit {{
                background: {colors['alternate_base']};
                border: 1px solid {colors['surface1']};
                padding: 8px;
                selection-background-color: {colors['highlight']};
            }}
            QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {colors['highlight']};
            }}

            /* Buttons */
            QPushButton {{
                background: {colors['button']};
                color: {colors['button_text']};
                border: 1px solid {colors['surface1']};
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background: {colors['surface1']};
                border-color: {colors['overlay0']};
            }}
            QPushButton:pressed {{
                background: {colors['overlay0']};
            }}
            QPushButton:disabled {{
                background: {colors['button']};
                color: {colors['disabled_text']};
                border-color: {colors['surface1']};
            }}

            /* Tabs */
            QTabWidget::pane {{
                border: 1px solid {colors['surface1']};
                margin-top: 4px;
                background: {colors['alternate_base']};
            }}
            QTabBar::tab {{
                background: {colors['button']};
                color: {colors['text']};
                padding: 8px 16px;
                margin-right: 4px;
                font-size: {cls._BASE_FONT_SIZE - 1}px;
            }}
            QTabBar::tab:selected {{
                background: {colors['highlight']};
                color: {colors['highlight_text']};
            }}
            QTabBar::tab:hover {{
                background: {colors['surface1']};
            }}

            /* Tables - Fixed rounded corners */
            QTableWidget {{
                background: {colors['button']};
                border: 1px solid {colors['surface1']};
                gridline-color: {colors['surface1']};
            }}
            QTableCornerButton::section {{
                background: {colors['button']};
                border: 1px solid {colors['surface1']};
            }}
            QHeaderView {{
                background: {colors['button']};
            }}
            QHeaderView::section {{
                background: {colors['button']};
                padding: 4px;
                border: 1px solid {colors['surface1']};
            }}
            QTableWidget::item {{
                padding: 4px;
            }}

            /* Menus & Toolbars - Fixed hover highlighting */
            QMenuBar {{
                background: {colors['base']};
                spacing: 4px;
            }}
            QMenuBar::item {{
                padding: 6px 12px;
                background: transparent;
            }}
            QMenuBar::item:selected {{
                background: {colors['surface1']};
            }}
            QMenuBar::item:pressed {{
                background: {colors['overlay0']};
            }}
            QMenu {{
                border: 1px solid {colors['surface1']};
                padding: 4px;
                background: {colors['base']};
                margin: 2px; /* Add some margin for the drop shadow */
            }}
            QMenu::item {{
                padding: 8px 16px;
                background-color: transparent;
            }}
            QMenu::icon {{
                padding: 8px;
            }}
            QMenu::item:selected {{
                background: {colors['highlight']};
                color: {colors['highlight_text']};
            }}
            QToolBar {{
                border-bottom: 1px solid {colors['surface1']};
                padding: 2px;
                spacing: 4px;
                background: {colors['base']};
            }}
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                padding: 4px;
            }}
            QToolButton:hover {{
                background: {colors['surface1']};
                border-color: {colors['surface1']};
            }}
            QToolButton:pressed {{
                background: {colors['overlay0']};
            }}

            /* Scrollbars */
            QScrollBar:vertical {{ width: 12px; }}
            QScrollBar:horizontal {{ height: 12px; }}
            QScrollBar::handle {{
                background: {colors['surface1']};
                margin: 2px;
            }}
            QScrollBar::handle:hover {{
                background: {colors['overlay0']};
            }}
        """
        app.setStyleSheet(stylesheet)

    @classmethod
    def apply_adaptive_styles(cls, app: QApplication) -> None:
        if cls.is_tablet_device(app):
            app.setStyleSheet(app.styleSheet() + f"""
                QWidget {{ font-size: {cls._TABLET_FONT_SIZE}px; }}
                QTabBar::tab {{ padding: 8px 16px; }}
            """)

    @staticmethod
    def is_tablet_device(app: QApplication) -> bool:
        screen = app.primaryScreen()
        diag = (screen.size().width()**2 + screen.size().height()**2)**0.5
        return (
            diag / screen.logicalDotsPerInch()
            <=
            DarkTheme._TABLET_DIAGONAL_INCH
        )


# region Exceptions


class ParseError(Exception):
    def __init__(
        self,
        message: str = "Ошибка разбора"
    ) -> None:
        super().__init__(message)


class FileServiceError(Exception):
    def __init__(
        self,
        message: str = "Ошибка файловой операции"
    ) -> None:
        super().__init__(message)


# endregion


# region Models


class TokenType(Enum):
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    LPAREN = auto()
    RPAREN = auto()
    ID = auto()
    WHITESPACE = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class ErrorInfo:
    line: int
    column: int
    message: str


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    line: int
    column: int


@dataclass(frozen=True)
class Quadruple:
    operator: str
    arg1: str
    arg2: str
    result: str
    line: int
    column: int


class AnalizationResult:
    def __init__(
        self,
        quadruples: List[Quadruple],
        errors: List[ErrorInfo]
    ) -> None:
        self.quadruples = quadruples
        self.errors = errors


# endregion


# region Protocols


class LexerProtocol(Protocol):
    def tokenize(
        self,
        text: str
    ) -> Tuple[List[Token], List[ErrorInfo]]:
        ...


class ParserProtocol(Protocol):
    def parse(
        self,
        tokens: List[Token]
    ) -> Tuple[List[Quadruple], List[ErrorInfo]]:
        ...


class ErrorHandlerProtocol(Protocol):
    def add_error(
        self,
        error: ErrorInfo
    ) -> None:
        ...

    def get_errors(self) -> List[ErrorInfo]:
        ...

    def clear(self) -> None:
        ...

    def has_errors(self) -> bool:
        ...


class LoggerProtocol(Protocol):
    def log(
        self,
        level: str,
        message: str,
        metadata: Dict[str, Any]
    ) -> None:
        ...

    def error(
        self,
        message: str,
        metadata: Dict[str, Any]
    ) -> None:
        ...

    def debug(
        self,
        message: str,
        metadata: Dict[str, Any]
    ) -> None:
        ...


class FileServiceProtocol(Protocol):
    def read(
        self,
        path: str
    ) -> str:
        ...

    def write(
        self,
        path: str,
        content: str
    ) -> None:
        ...


# endregion


# region Services


class AnalizerService:
    def __init__(
        self,
        lexer: LexerProtocol,
        parser: ParserProtocol,
        logger: LoggerProtocol,
    ) -> None:
        self._lexer = lexer
        self._parser = parser
        self._logger = logger

    def analize(
        self,
        code: str
    ) -> AnalizationResult:
        try:
            self._logger.debug(
                "Начало анализации",
                {"code_length": len(code)}
            )

            if hasattr(
                self._lexer,
                '_error_handler'
            ):
                self._lexer._error_handler.clear()  # pyright: ignore
            if hasattr(
                self._parser,
                '_error_handler'
            ):
                self._parser._error_handler.clear()  # pyright: ignore

            tokens, lex_errors = self._lexer.tokenize(code)
            self._log_errors(
                lex_errors,
                "Лексический анализ"
            )

            quadruples, parse_errors = self._parser.parse(tokens)
            self._log_errors(
                parse_errors,
                "Синтаксический анализ"
            )

            return AnalizationResult(
                quadruples,
                lex_errors + parse_errors
            )
        except Exception as e:
            self._logger.error(
                "Ошибка анализа",
                {"exception": str(e)}
            )
            raise

    def _log_errors(
        self,
        errors: List[ErrorInfo],
        stage: str
    ) -> None:
        for error in errors:
            self._logger.error(
                f"{stage} ошибка",
                {
                    "line": error.line,
                    "column": error.column,
                    "message": error.message,
                }
            )


T = TypeVar('T')


class Command(Generic[T]):
    @abstractmethod
    def execute(self) -> T:
        ...


class FileReadCommand(Command[str]):
    def __init__(
        self,
        path: str,
        service: FileServiceProtocol
    ) -> None:
        self._path = path
        self._service = service

    def execute(self) -> str:
        return self._service.read(self._path)


class FileWriteCommand(Command[None]):
    def __init__(
        self,
        path: str,
        content: str,
        service: FileServiceProtocol
    ) -> None:
        self._path = path
        self._content = content
        self._service = service

    def execute(self) -> None:
        self._service.write(self._path, self._content)


# endregion


# region Handlers


class ErrorHandler(ErrorHandlerProtocol):
    def __init__(self) -> None:
        self._errors: List[ErrorInfo] = []

    def add_error(
        self,
        error: ErrorInfo
    ) -> None:
        self._errors.append(error)

    def get_errors(self) -> List[ErrorInfo]:
        return self._errors.copy()

    def clear(self) -> None:
        self._errors.clear()

    def has_errors(self) -> bool:
        return bool(self._errors)

    def __len__(self) -> int:
        return len(self._errors)


class PositionTracker:
    def __init__(self) -> None:
        self._line = 1
        self._column = 1

    def update(
        self,
        text: str
    ) -> None:
        lines = text.split('\n')
        if len(lines) > 1:
            self._line += len(lines) - 1
            self._column = len(lines[-1]) + 1
        else:
            self._column += len(text)

    @property
    def line(self) -> int:
        return self._line

    @property
    def column(self) -> int:
        return self._column


# endregion


# region Implementations


class RegexLexer(LexerProtocol):
    _TOKEN_SPECS = [
        (TokenType.PLUS, r'\+'),
        (TokenType.MINUS, r'-'),
        (TokenType.MULTIPLY, r'\*'),
        (TokenType.DIVIDE, r'/'),
        (TokenType.LPAREN, r'\('),
        (TokenType.RPAREN, r'\)'),
        (TokenType.ID, r'[a-zA-Z]+'),
        (TokenType.WHITESPACE, r'\s+'),
    ]

    def __init__(
        self,
        error_handler: ErrorHandlerProtocol,
        logger: LoggerProtocol
    ) -> None:
        self._error_handler = error_handler
        self._logger = logger
        self._regex = self._build_regex()
        self._token_start_chars = {
            '+', '-', '*', '/',
            '(', ')', ' ', '\t',
            '\n', '\r'
        }

    def _build_regex(self) -> re.Pattern:
        regex_parts = [
            f'(?P<{token_type.name}>{pattern})'
            for token_type, pattern in self._TOKEN_SPECS
        ]
        return re.compile(
            '|'.join(regex_parts),
            re.MULTILINE
        )

    def tokenize(
        self,
        text: str
    ) -> Tuple[List[Token], List[ErrorInfo]]:
        try:
            if not text:
                self._error_handler.add_error(
                    ErrorInfo(0, 0, "Пустой ввод")
                )
                return (
                    [],
                    self._error_handler.get_errors()
                )

            tokens: List[Token] = []
            tracker = PositionTracker()
            pos = 0

            while pos < len(text):
                match = self._regex.match(
                    text,
                    pos
                )
                if match:
                    self._process_match(
                        match,
                        tokens,
                        tracker
                    )
                    pos = match.end()
                else:
                    pos = self._process_unmatched(
                        text,
                        pos,
                        tracker
                    )

            return (
                tokens,
                self._error_handler.get_errors()
            )
        except Exception as e:
            self._logger.error(
                "Ошибка токенизации",
                {"exception": str(e)}
            )
            raise

    def _process_match(
        self,
        match: re.Match,
        tokens: List[Token],
        tracker: PositionTracker
    ) -> None:
        token_type = TokenType[match.lastgroup]  # type: ignore
        value = match.group()
        if token_type != TokenType.WHITESPACE:
            tokens.append(Token(
                type=token_type,
                value=value,
                line=tracker.line,
                column=tracker.column
            ))
        tracker.update(value)

    def _process_unmatched(
        self,
        text: str,
        pos: int,
        tracker: PositionTracker
    ) -> int:
        start_pos = pos
        start_line = tracker.line
        start_column = tracker.column

        while pos < len(text):
            c = text[pos]
            if c in self._token_start_chars or c.isspace():
                break
            pos += 1

        if start_pos > 0 and text[start_pos - 1].isalpha():
            garbage = text[start_pos - 1:pos]
            self._handle_invalid_characters(
                garbage,
                start_line,
                start_column - 1
            )
            tracker.update(garbage)
        else:
            garbage = text[start_pos:pos]
            self._handle_invalid_characters(
                garbage,
                start_line,
                start_column
            )
            tracker.update(garbage)

        return pos

    def _handle_invalid_characters(
        self,
        garbage: str,
        line: int,
        column: int
    ) -> None:
        corrected = ''.join([c for c in garbage if c.isalpha()])
        if corrected:
            error_msg = f"Заменить '{garbage}' на '{corrected}'"
            self._error_handler.add_error(
                ErrorInfo(
                    line,
                    column,
                    error_msg
                )
            )
        else:
            error_msg = f"Неожиданный токен: '{garbage}'"
            self._error_handler.add_error(
                ErrorInfo(
                    line,
                    column,
                    error_msg
                )
            )


class RecursiveDescentParser(ParserProtocol):
    def __init__(
        self,
        error_handler: ErrorHandlerProtocol,
        logger: LoggerProtocol
    ) -> None:
        self._error_handler = error_handler
        self._logger = logger
        self._tokens: List[Token] = []
        self._current_pos = 0
        self._generator = QuadrupleGenerator()

    def parse(
        self,
        tokens: List[Token]
    ) -> Tuple[List[Quadruple], List[ErrorInfo]]:
        try:
            self._reset_state(tokens)
            if not tokens:
                self._report_error("Пустой ввод")
                return (
                    [],
                    self._error_handler.get_errors()
                )

            self._parse_expression()
            self._check_remaining_tokens()

            return (
                self._generator.get_quadruples(),
                self._error_handler.get_errors()
            )
        except Exception as e:
            self._logger.error(
                "Ошибка парсинга",
                {"exception": str(e)}
            )
            raise

    def _reset_state(
        self,
        tokens: List[Token]
    ) -> None:
        self._tokens = tokens
        self._current_pos = 0
        self._error_handler.clear()
        self._generator = QuadrupleGenerator()

    def _parse_expression(self) -> str:
        left = self._parse_term()
        return self._parse_expression_tail(left)

    def _parse_expression_tail(
        self,
        left: str
    ) -> str:
        while self._match_operator(
            {
                TokenType.PLUS,
                TokenType.MINUS
            }
        ):
            op_token = self._consume()
            right = self._parse_term()
            left = self._emit_operation(
                op_token,
                left,
                right
            )
        return left

    def _parse_term(self) -> str:
        left = self._parse_factor()
        return self._parse_term_tail(left)

    def _parse_term_tail(
        self,
        left: str
    ) -> str:
        while self._match_operator(
            {
                TokenType.MULTIPLY,
                TokenType.DIVIDE
            }
        ):
            op_token = self._consume()
            right = self._parse_factor()
            left = self._emit_operation(
                op_token,
                left,
                right
            )
        return left

    def _parse_factor(self) -> str:
        if self._match(TokenType.LPAREN):
            self._consume()
            expr = self._parse_expression()
            if not self._match(TokenType.RPAREN):
                self._report_error("Несогласованные скобки")
            self._consume()
            return expr
        return self._parse_identifier()

    def _emit_operation(
        self,
        op_token: Token,
        left: str,
        right: str
    ) -> str:
        temp = self._generator.new_temp()
        self._generator.emit(
            operator=op_token.value,
            arg1=left,
            arg2=right,
            result=temp,
            line=op_token.line,
            column=op_token.column
        )
        return temp

    def _check_remaining_tokens(self) -> None:
        if self._has_more_tokens():
            remaining = self._current_token
            msg = (
                f"Неожиданные токены: '{remaining.value}'"
                if remaining
                else "Неожиданный конец ввода"
            )
            self._report_error(msg)

    def _report_error(
        self,
        message: str
    ) -> None:
        token = self._current_token
        error = ErrorInfo(
            token.line if token else 0,
            token.column if token else 0,
            message
        )
        self._error_handler.add_error(error)

    def _has_more_tokens(self) -> bool:
        return self._current_pos < len(self._tokens)

    @property
    def _current_token(self) -> Optional[Token]:
        if self._current_pos >= len(self._tokens):
            return None
        return self._tokens[self._current_pos]

    def _consume(self) -> Token:
        if not self._has_more_tokens():
            self._report_error("Неожиданное завершение ввода")
            raise ParseError()
        token = self._tokens[self._current_pos]
        self._current_pos += 1
        return token

    def _match(
        self,
        token_type: TokenType
    ) -> bool:
        if not self._current_token:
            return False
        return self._current_token.type == token_type

    def _match_operator(
        self,
        types: set[TokenType]
    ) -> bool:
        if not self._current_token:
            return False
        return self._current_token.type in types

    def _parse_identifier(self) -> str:
        current_token = self._current_token
        if not self._match(TokenType.ID):
            if current_token:
                msg = (
                    f"Неожиданный оператор '{current_token.value}' "
                    "вместо идентификатора"
                    if current_token.type in {
                        TokenType.PLUS, TokenType.MINUS,
                        TokenType.MULTIPLY, TokenType.DIVIDE
                    }
                    else (
                        "Ожидается идентификатор, но "
                        f"получено '{current_token.value}'"
                    )
                )
            else:
                msg = "Ожидается идентификатор, но ввод завершен"
            self._report_error(msg)
            return ""
        token = self._consume()
        return token.value


# endregion


# region Adapters


class ConsoleLogger(LoggerProtocol):
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._configure_logging()

    def _configure_logging(self) -> None:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def log(
        self,
        level: str,
        message: str,
        metadata: Dict[str, Any]
    ) -> None:
        getattr(
            self._logger,
            level
        )(f"{message} | {metadata}")

    def error(
        self,
        message: str,
        metadata: Dict[str, Any]
    ) -> None:
        self.log(
            'error',
            message,
            metadata
        )

    def debug(
        self,
        message: str,
        metadata: Dict[str, Any]
    ) -> None:
        self.log(
            'debug',
            message,
            metadata
        )


class FileServiceAdapter(FileServiceProtocol):
    def read(
        self,
        path: str
    ) -> str:
        try:
            with open(
                path,
                'r',
                encoding='utf-8'
            ) as f:
                return f.read()
        except IOError as e:
            raise FileServiceError(f"Ошибка чтения: {e}")

    def write(
        self,
        path: str,
        content: str
    ) -> None:
        try:
            with open(
                path,
                'w',
                encoding='utf-8'
            ) as f:
                f.write(content)
        except IOError as e:
            raise FileServiceError(f"Ошибка записи: {e}")


# endregion


# region Generators


class QuadrupleGenerator:

    def __init__(self) -> None:
        self._quadruples: List[Quadruple] = []
        self._temp_counter = 0

    def emit(
        self,
        operator: str,
        arg1: str,
        arg2: str,
        result: str,
        line: int,
        column: int
    ) -> None:
        self._quadruples.append(Quadruple(
            operator=operator,
            arg1=arg1,
            arg2=arg2,
            result=result,
            line=line,
            column=column
        ))

    def new_temp(self) -> str:
        self._temp_counter += 1
        return f't{self._temp_counter}'

    def get_quadruples(self) -> List[Quadruple]:
        return self._quadruples.copy()


# endregion


# region UI Layer


class TextEditor(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self._configure_editor()

    def _configure_editor(self) -> None:
        self.setFont(QFont("Fira Code", 12))


class ResultsView(QTabWidget):
    def __init__(self) -> None:
        super().__init__()
        self._init_tabs()

    def _init_tabs(self) -> None:
        self._quadruples_table = self._create_table(
            [
                "Операция",
                "Аргумент 1",
                "Аргумент 2",
                "Результат"
            ]
        )
        self._errors_table = self._create_table(
            [
                "Строка",
                "Колонка",
                "Сообщение"
            ]
        )

        self.addTab(
            self._quadruples_table,
            "Тетрады"
        )
        self.addTab(
            self._errors_table,
            "Ошибки"
        )

    def _create_table(
        self,
        headers: List[str]
    ) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    def display_results(
        self,
        result: AnalizationResult
    ) -> None:
        self._update_table(
            self._errors_table,
            result.errors,
            lambda e: [
                str(e.line),
                str(e.column),
                e.message
            ]
        )
        self._update_table(
            self._quadruples_table,
            result.quadruples if not result.errors else [],
            lambda q: [
                q.operator,
                q.arg1,
                q.arg2,
                q.result
            ]
        )

    def _update_table(
        self,
        table: QTableWidget,
        items: Sequence[Any],
        mapper: Callable[[Any], List[str]]
    ) -> None:
        table.setRowCount(len(items))
        for row, item in enumerate(items):
            for col, value in enumerate(mapper(item)):
                table.setItem(
                    row,
                    col,
                    QTableWidgetItem(value)
                )


class MainWindow(QMainWindow):
    _open_file_requested = Signal(str)
    _save_file_requested = Signal(str)
    _analize_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()
        self._create_menu()

    def _init_ui(self) -> None:
        self.setWindowTitle("Анализатор")
        self.resize(1024, 768)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        self._editor = TextEditor()
        self._results_view = ResultsView()

        layout.addWidget(self._editor, 3)
        layout.addWidget(self._results_view, 2)

        self.setCentralWidget(central_widget)

    def _create_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("Файл")
        open_action = QAction("Открыть", self)
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        save_action = QAction("Сохранить", self)
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        analyzer_menu = menu.addMenu("Анализатор")
        analyzer_action = QAction("Запустить", self)
        analyzer_action.setShortcut(QKeySequence("Ctrl+R"))
        analyzer_action.triggered.connect(self._analize_requested.emit)
        analyzer_menu.addAction(analyzer_action)

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть файл",
            "",
            "Текстовые файлы (*.txt)"
        )
        if path:
            self._open_file_requested.emit(path)

    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить файл",
            "",
            "Текстовые файлы (*.txt)"
        )
        if path:
            self._save_file_requested.emit(path)

    def show_error(self, message: str) -> None:
        QMessageBox.critical(
            self,
            "Ошибка",
            message
        )

    @property
    def code(self) -> str:
        return self._editor.toPlainText()

    @code.setter
    def code(self, value: str) -> None:
        self._editor.setPlainText(value)


# endregion


# region Composition Root


class ApplicationController(QObject):
    def __init__(
        self,
        window: MainWindow,
        analizer: AnalizerService,
        file_service: FileServiceProtocol
    ) -> None:
        super().__init__()
        self._window = window
        self._analizer = analizer
        self._file_service = file_service
        self._connect_signals()

    def _connect_signals(self) -> None:
        self._window._open_file_requested.connect(self._handle_open)
        self._window._save_file_requested.connect(self._handle_save)
        self._window._analize_requested.connect(self._handle_analize)

    def _handle_open(
        self,
        path: str
    ) -> None:
        try:
            cmd = FileReadCommand(
                path,
                self._file_service
            )
            content = cmd.execute()
            self._window.code = content
        except FileServiceError as e:
            self._window.show_error(str(e))

    def _handle_save(
        self,
        path: str
    ) -> None:
        try:
            cmd = FileWriteCommand(
                path,
                self._window.code,
                self._file_service
            )
            cmd.execute()
        except FileServiceError as e:
            self._window.show_error(str(e))

    def _handle_analize(self) -> None:
        result = self._analizer.analize(self._window.code)
        self._window._results_view.display_results(result)


def bootstrap() -> Tuple[MainWindow, ApplicationController]:
    error_handler = ErrorHandler()
    logger = ConsoleLogger()
    file_service = FileServiceAdapter()

    lexer = RegexLexer(error_handler, logger)
    parser = RecursiveDescentParser(error_handler, logger)
    analizer = AnalizerService(lexer, parser, logger)

    window = MainWindow()
    controller = ApplicationController(window, analizer, file_service)

    return window, controller


# endregion


if __name__ == "__main__":
    app = QApplication(sys.argv)
    DarkTheme.apply_theme(app)
    window, _ = bootstrap()
    window.show()
    sys.exit(app.exec())
