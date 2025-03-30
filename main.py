import os
import re
import sys
import bisect
import locale
from functools import partial
from queue import PriorityQueue
from typing import (
    List,
    Tuple,
    Callable,
    Optional,
)
from PySide6.QtCore import (
    Qt,
    QRect,
    QSize,
    Signal,
    QLocale,
    QObject,
    QFileSystemWatcher,
    QRegularExpression,
)
from PySide6.QtGui import (
    QFont,
    QIcon,
    QColor,
    QAction,
    QPainter,
    QPalette,
    QShortcut,
    QKeySequence,
    QTextCharFormat,
    QSyntaxHighlighter,
)
from PySide6.QtWidgets import (
    QMenu,
    QWidget,
    QMenuBar,
    QToolBar,
    QTextEdit,
    QTabWidget,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QApplication,
    QTableWidget,
    QPlainTextEdit,
    QTableWidgetItem,
)


class DarkTheme:
    """Catppuccin Mocha dark theme with comprehensive styling."""

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
        "syntax_keyword": "#f38ba8",
        "syntax_type": "#89b4fa",
        "syntax_string": "#94e2d5",
        "syntax_comment": "#6c7086",
        "syntax_number": "#fab387",
        "syntax_function": "#f5c2e7",
        "current_line": "#313244",
        "graph_colors": [
            "#b4befe", "#f5c2e7", "#74c7ec",
            "#94e2d5", "#fab387", "#f9e2af"
        ]
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


class Token:
    def __init__(
        self,
        type: str,
        value: str,
        line: int,
        column: int
    ):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type}, {self.value}, {self.line}, {self.column})"


class LexerError:
    def __init__(
        self,
        line: int,
        column: int,
        message: str
    ):
        self.line = line
        self.column = column
        self.message = message

    def __repr__(self):
        return f"LexerError({self.line}, {self.column}, {self.message})"


class Branch:
    def __init__(
        self,
        tokens: List[Token],
        index: int,
        current_state: str,
        edit_count: int,
        changes: List[tuple]
    ):
        self.tokens = tokens
        self.index = index
        self.current_state = current_state
        self.edit_count = edit_count
        self.changes = changes

    def __lt__(self, other):
        return self.edit_count < other.edit_count


class AdvancedLexer:
    MAX_EDIT_COUNT = 15

    TOKEN_REGEX = [
        (r'const\b', 'CONST'),
        (r'i32\b', 'I32'),
        (r':', 'COLON'),
        (r'=', 'ASSIGN'),
        (r'\+', 'PLUS'),
        (r'-', 'MINUS'),
        (r';', 'SEMICOLON'),
        (r'[a-zA-Z_][^ \t\n\r:;=+]*', 'IDENTIFIER'),
        (r'\d[^ \t\n\r:;=+]*', 'NUMBER'),
        (r'[^\s]', 'INVALID'),
    ]

    DEFAULT_TOKEN_VALUES = {
        'CONST': 'const', 'I32': 'i32', 'COLON': ':',
        'ASSIGN': '=', 'IDENTIFIER': 'имя_переменной',
        'PLUS': '+', 'MINUS': '-', 'SEMICOLON': ';',
        'NUMBER': 'число'
    }

    TRANSITIONS = {
        'START': {'CONST': 'CONSTIDENTIFIER'},
        'CONSTIDENTIFIER': {'IDENTIFIER': 'COLON'},
        'COLON': {'COLON': 'DATATYPE'},
        'DATATYPE': {'I32': 'ASSIGNMENT'},
        'ASSIGNMENT': {'ASSIGN': 'VALUE'},
        'VALUE': {'NUMBER': 'SEMICOLON', 'MINUS': 'WHOLENUMBER'},
        'WHOLENUMBER': {'NUMBER': 'SEMICOLON'},
        'SEMICOLON': {'SEMICOLON': 'END'},
        'END': {}
    }

    KEYWORDS = {'const', 'i32'}
    KEYWORD_TO_TOKEN = {'const': 'CONST', 'i32': 'I32'}
    KEYWORD_TOLERANCE = 2

    def __init__(self, input_text: str):
        self.input_text = input_text
        self.newline_positions = [
            i for i, c in enumerate(input_text) if c == '\n']
        self.tokens = []
        self.errors = []
        self.pos = 0
        self.length = len(input_text)

    def get_line_column(self, pos: int) -> Tuple[int, int]:
        line_num = bisect.bisect_right(self.newline_positions, pos) + 1
        if line_num > 1:
            column = pos - self.newline_positions[line_num - 2]
        else:
            column = pos + 1
        return line_num, column

    def create_token(self, token_type: str, reference_token: 'Token', insert_after: bool = False) -> 'Token':
        value = self.DEFAULT_TOKEN_VALUES.get(token_type, token_type)
        if reference_token:
            if insert_after:
                new_pos = reference_token.column + len(reference_token.value)
                return Token(token_type, value, reference_token.line, new_pos)
            return Token(token_type, value, reference_token.line, reference_token.column)

    def _is_keyword_candidate(self, value: str) -> bool:
        value_lower = value.lower()
        for keyword in self.KEYWORDS:
            if len(value) < len(keyword) - self.KEYWORD_TOLERANCE:
                continue
            if self._fuzzy_match(value_lower, keyword):
                return True
        return False

    def _fuzzy_match(self, s: str, target: str) -> bool:
        if not s or not target:
            return False
        if s[0] != target[0]:
            return False
        max_length = max(len(s), len(target))
        matches = 0
        s_idx, t_idx = 0, 0
        while s_idx < len(s) and t_idx < len(target):
            if s[s_idx] == target[t_idx]:
                matches += 1
                s_idx += 1
                t_idx += 1
            else:
                t_idx += 1
        return matches / len(target) >= 0.6

    def _correct_keyword(self, value: str) -> str:
        value_lower = value.lower()
        for keyword in self.KEYWORDS:
            if self._fuzzy_match(value_lower, keyword):
                return keyword
        return None

    def lex(self) -> Tuple[List[Token], List[LexerError]]:
        while self.pos < self.length:
            while self.pos < self.length and self.input_text[self.pos].isspace():
                self.pos += 1
            if self.pos >= self.length:
                break

            line, column = self.get_line_column(self.pos)
            matched = False

            for pattern, token_type in self.TOKEN_REGEX:
                regex = re.compile(pattern)
                match = regex.match(self.input_text, self.pos)
                if match:
                    value = match.group(0)
                    start_pos = self.pos
                    self.pos = match.end()

                    if token_type == 'IDENTIFIER':
                        original = value
                        valid_chars = []
                        has_errors = False

                        if not (original[0].isalpha() or original[0] == '_'):
                            self.errors.append(LexerError(
                                line, column,
                                f"Недопустимый первый символ идентификатора: {
                                    original[0]}"
                            ))
                            has_errors = True
                        else:
                            valid_chars.append(original[0])

                        for i in range(1, len(original)):
                            c = original[i]
                            if c.isalnum() or c == '_':
                                valid_chars.append(c)
                            else:
                                err_pos = start_pos + i
                                line_err, column_err = self.get_line_column(
                                    err_pos)
                                """
                                self.errors.append(LexerError(
                                    line_err, column_err,
                                    f"Недопустимый символ в идентификаторе: {
                                        repr(c)}"
                                ))
                                """
                                has_errors = True

                        valid_value = ''.join(valid_chars) or '_'
                        if valid_value in self.KEYWORDS:
                            keyword_token_type = self.KEYWORD_TO_TOKEN[valid_value]
                            self.tokens.append(
                                Token(keyword_token_type, valid_value, line, column))
                            if has_errors:
                                self.errors.append(LexerError(
                                    line, column,
                                    f"Исправлено '{original}' на '{
                                        valid_value}'"
                                ))
                        else:
                            self.tokens.append(
                                Token('IDENTIFIER', valid_value, line, column))
                            if has_errors:
                                self.errors.append(LexerError(
                                    line, column,
                                    f"Исправлен идентификатор: '{
                                        original}' -> '{valid_value}'"
                                ))
                        matched = True
                        break

                    elif token_type == 'NUMBER':
                        original = value
                        cleaned = []
                        has_errors = False
                        for i, c in enumerate(original):
                            if c.isdigit():
                                cleaned.append(c)
                            else:
                                err_pos = start_pos + i
                                line_err, column_err = self.get_line_column(
                                    err_pos)
                                """
                                self.errors.append(LexerError(
                                    line_err, column_err,
                                    f"Недопустимый символ в числе: {repr(c)}"
                                ))
                                """
                                has_errors = True

                        valid_value = ''.join(cleaned) or '0'
                        self.tokens.append(
                            Token('NUMBER', valid_value, line, column))
                        if has_errors:
                            self.errors.append(LexerError(
                                line, column,
                                f"Исправлено число: '{
                                    original}' -> '{valid_value}'"
                            ))
                        matched = True
                        break

                    else:
                        self.tokens.append(
                            Token(token_type, value, line, column))
                        matched = True
                        break

            if not matched:
                char = self.input_text[self.pos]
                self.errors.append(LexerError(
                    line, column, f"Необрабатываемый символ: {repr(char)}"))
                self.pos += 1

        return self.tokens, self.errors

    def validate_tokens(self) -> Tuple[List[Token], List[LexerError]]:
        queue = PriorityQueue()
        queue.put((
            0,
            Branch(
                self.tokens.copy(), 0, 'START', 0, []
            )
        ))
        best = None

        while not queue.empty():
            _, branch = queue.get()

            if best and best.edit_count <= self.MAX_EDIT_COUNT:
                break

            if branch.index >= len(branch.tokens):
                if branch.current_state in ('END', 'START'):
                    if not best or branch.edit_count < best.edit_count:
                        best = branch
                else:
                    self._process_transitions(
                        queue,
                        branch
                    )
            else:
                current_token = branch.tokens[branch.index]
                allowed = self.TRANSITIONS.get(
                    branch.current_state,
                    {}
                ).keys()

                if current_token.type in allowed:
                    self._handle_valid_transition(
                        queue,
                        branch
                    )
                else:
                    self._generate_repair_branches(
                        queue,
                        branch,
                        current_token,
                        allowed
                    )

        return self._finalize_validation(best)

    def _process_transitions(self, queue, branch):
        current_state = branch.current_state
        allowed = self.TRANSITIONS.get(
            current_state,
            {}
        ).keys()

        for insert_type in allowed:
            line, column = 1, 1
            if branch.tokens:
                last_token = branch.tokens[-1]
                line = last_token.line
                column = last_token.column + len(last_token.value)

            insert_token = Token(
                insert_type,
                self.DEFAULT_TOKEN_VALUES.get(
                    insert_type,
                    insert_type
                ),
                line,
                column
            )
            new_tokens = branch.tokens.copy()
            new_tokens.append(insert_token)
            new_changes = branch.changes.copy()
            new_changes.append(('insert', len(new_tokens)-1, insert_token))
            next_state = self.TRANSITIONS[current_state][insert_type]

            if branch.edit_count + 1 <= self.MAX_EDIT_COUNT:
                new_branch = Branch(
                    tokens=new_tokens,
                    index=len(new_tokens),
                    current_state=next_state,
                    edit_count=branch.edit_count + 1,
                    changes=new_changes
                )
                queue.put((
                    new_branch.edit_count,
                    new_branch
                ))

    def _handle_valid_transition(self, queue, branch):
        current_token = branch.tokens[branch.index]
        next_state = self.TRANSITIONS[branch.current_state][current_token.type]

        new_edit_count = branch.edit_count if next_state != 'END' else 0
        new_state = 'START' if next_state == 'END' else next_state

        new_branch = Branch(
            tokens=branch.tokens,
            index=branch.index + 1,
            current_state=new_state,
            edit_count=new_edit_count,
            changes=branch.changes.copy()
        )
        queue.put((new_branch.edit_count, new_branch))

    def _generate_repair_branches(
        self,
        queue,
        branch,
        current_token,
        allowed
    ):
        self._generate_delete_branch(queue, branch, current_token)
        self._generate_replace_branches(queue, branch, current_token, allowed)
        self._generate_insert_branches(queue, branch, current_token, allowed)

    def _generate_delete_branch(self, queue, branch, current_token):
        new_tokens = branch.tokens.copy()
        del new_tokens[branch.index]
        new_changes = branch.changes.copy()
        new_changes.append((
            'delete',
            branch.index,
            current_token
        ))
        if branch.edit_count + 1 <= self.MAX_EDIT_COUNT:
            new_branch = Branch(
                tokens=new_tokens,
                index=branch.index,
                current_state=branch.current_state,
                edit_count=branch.edit_count + 1,
                changes=new_changes
            )
            queue.put((
                new_branch.edit_count,
                new_branch
            ))

    def _generate_replace_branches(
        self,
        queue,
        branch,
        current_token,
        allowed
    ):
        current_state = branch.current_state
        for replace_type in allowed:
            new_token = self.create_token(replace_type, current_token)
            new_tokens = branch.tokens.copy()
            new_tokens[branch.index] = new_token
            new_changes = branch.changes.copy()
            new_changes.append((
                'replace',
                branch.index,
                current_token,
                new_token
            ))
            next_state = self.TRANSITIONS[current_state][replace_type]
            if branch.edit_count + 1 <= self.MAX_EDIT_COUNT:
                new_branch = Branch(
                    tokens=new_tokens,
                    index=branch.index + 1,
                    current_state=next_state,
                    edit_count=branch.edit_count + 1,
                    changes=new_changes
                )
                queue.put((
                    new_branch.edit_count,
                    new_branch
                ))

    def _generate_insert_branches(
        self,
        queue,
        branch,
        current_token,
        allowed
    ):
        current_state = branch.current_state
        for insert_type in allowed:
            insert_token = self.create_token(
                insert_type,
                current_token,
                False
            )
            new_tokens = branch.tokens.copy()
            new_tokens.insert(branch.index, insert_token)
            new_changes = branch.changes.copy()
            new_changes.append(('insert', branch.index, insert_token))
            next_state = self.TRANSITIONS[current_state][insert_type]
            if branch.edit_count + 1 <= self.MAX_EDIT_COUNT:
                new_branch = Branch(
                    tokens=new_tokens,
                    index=branch.index + 1,
                    current_state=next_state,
                    edit_count=branch.edit_count + 1,
                    changes=new_changes
                )
                queue.put((new_branch.edit_count, new_branch))

    def _finalize_validation(self, best):
        if best:
            self.tokens = best.tokens
            errors = self._generate_errors_from_changes(best.changes)
            return self.tokens, errors
        return self.tokens, self.errors + [
            LexerError(
                0, 0, f"Превышен лимит исправлений ({self.MAX_EDIT_COUNT})"
            )
        ]

    def _generate_errors_from_changes(
        self,
        changes: List[tuple]
    ) -> List[LexerError]:
        errors = []
        for change in changes:
            action = change[0]
            if action == 'delete':
                *_, token = change
                errors.append(
                    LexerError(
                        token.line,
                        token.column,
                        f"Удаление недопустимого токена: '{token.value}'"
                    )
                )
            elif action == 'replace':
                *_, old_token, new_token = change
                errors.append(
                    LexerError(
                        old_token.line,
                        old_token.column,
                        f"Замена '{old_token.value}' на '{new_token.value}'"
                    )
                )
            elif action == 'insert':
                *_, token = change
                errors.append(
                    LexerError(
                        token.line,
                        token.column,
                        f"Вставка отсутствующего токена: '{token.value}'"
                    )
                )
        return errors


class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.rules = []
        self._init_highlight_rules()

    def _init_highlight_rules(self):
        self._add_rule(
            ["if", "else", "elif", "while", "for", "return", "break",
             "continue", "function", "class", "try", "catch", "finally",
             "var", "let", "const", "new", "this", "super", "import",
             "export", "default", "async", "await", "true", "false", "null"],
            QColor(
                DarkTheme.get_color("syntax_keyword")
            ),
            bold=True
        )
        self._add_rule(
            ["number", "string", "boolean", "object", "array", "void",
             "any", "undefined", "symbol", "never", "type", "interface"],
            QColor(
                DarkTheme.get_color("syntax_type")
            ),
            italic=True
        )
        self._add_string_rule(QColor(DarkTheme.get_color("syntax_string")))
        self._add_comment_rule(QColor(DarkTheme.get_color("syntax_comment")))
        self._add_number_rule(QColor(DarkTheme.get_color("syntax_number")))
        self._add_function_rule(QColor(DarkTheme.get_color("syntax_function")))

    def _add_rule(self, keywords, color, bold=False, italic=False):
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        fmt.setFontWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
        fmt.setFontItalic(italic)

        for word in keywords:
            pattern = QRegularExpression(
                r"\b" + QRegularExpression.escape(word) + r"\b"
            )
            if pattern.isValid():
                self.rules.append((pattern, fmt))

    def _add_string_rule(self, color):
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        patterns = (
            QRegularExpression(
                r'"[^"\\]*(\\.[^"\\]*)*"'
            ),
            QRegularExpression(
                r"'[^'\\]*(\\.[^'\\]*)*'"
            ),
            QRegularExpression(
                r"`[^`\\]*(\\.[^`\\]*)*`"
            )
        )
        for pattern in patterns:
            if pattern.isValid():
                self.rules.append((pattern, fmt))

    def _add_comment_rule(self, color):
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        fmt.setFontItalic(True)
        patterns = (
            QRegularExpression(
                r"//[^\n]*"
            ),
            QRegularExpression(
                r"/\*.*?\*/",
                QRegularExpression.PatternOption.DotMatchesEverythingOption
            )
        )
        for pattern in patterns:
            if pattern.isValid():
                self.rules.append((pattern, fmt))

    def _add_number_rule(self, color):
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        pattern = QRegularExpression(
            r"\b\d+(\.\d+)?([eE][+-]?\d+)?\b"
        )
        if pattern.isValid():
            self.rules.append((pattern, fmt))

    def _add_function_rule(self, color):
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        fmt.setFontItalic(True)
        pattern = QRegularExpression(
            r"\b\w+(?=\()"
        )
        if pattern.isValid():
            self.rules.append((pattern, fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    fmt
                )
        self.setCurrentBlockState(0)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.bg_color = QColor(
            DarkTheme.get_color("surface1")
        )
        self.text_color = QColor(
            DarkTheme.get_color("overlay0")
        )

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.bg_color)

        block = self.editor.firstVisibleBlock()
        block_num = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(
            self.editor.contentOffset()
        ).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(self.text_color)
                painter.drawText(
                    0,
                    int(top),
                    self.width() - 4,
                    self.editor.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_num + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            block_num += 1


class TextEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.current_line_format = QTextCharFormat()
        self.current_line_format.setBackground(
            QColor(
                DarkTheme.get_color("current_line")
            )
        )

        self.setup_connections()
        self._update_line_number_width(0)
        self.setFont(QFont("Fira Code", 12))
        self.highlighter = SyntaxHighlighter(self.document())

    def setup_connections(self):
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_numbers)
        self.cursorPositionChanged.connect(self._highlight_current_line)

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 20 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_width(self, _):
        self.setViewportMargins(
            self.line_number_area_width(), 0, 0, 0
        )

    def _update_line_numbers(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(
                cr.left(),
                cr.top(),
                self.line_number_area_width(),
                cr.height()
            )
        )

    def _highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format = self.current_line_format  # type: ignore
            selection.cursor = self.textCursor()  # type: ignore
            selection.cursor.clearSelection()  # type: ignore
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() in (
            Qt.Key.Key_Return,
            Qt.Key.Key_Tab,
            Qt.Key.Key_Backspace,
            Qt.Key.Key_Delete
        ):
            self._highlight_current_line()

    def wheelEvent(self, event):
        super().wheelEvent(event)
        self._highlight_current_line()


class DocumentModel(QObject):
    modified = Signal(bool)
    file_path_changed = Signal(str, str)

    def __init__(self):
        super().__init__()
        self._file_path = None
        self._is_modified = False

    @property
    def file_path(self):
        return self._file_path

    @file_path.setter
    def file_path(self, value):
        if not isinstance(
            value,
            (
                str,
                type(None)
            )
        ):
            raise TypeError(
                "Путь должен быть строкой или None"
            )
        old_value = self._file_path
        self._file_path = value
        self.file_path_changed.emit(str(old_value), str(value))

    @property
    def is_modified(self):
        return self._is_modified

    @is_modified.setter
    def is_modified(self, value):
        if not isinstance(
            value,
            bool
        ):
            raise TypeError(
                "Флаг изменения должен быть логическим значением"
            )
        self._is_modified = value
        self.modified.emit(value)


class DocumentWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_connected = False
        self._is_reloading = False
        self._is_saving_internally = False
        self.last_saved_mtime = None

        self.model = DocumentModel()
        self.main_layout = QVBoxLayout(self)

        self.input_edit = TextEditor()
        self.highlighter = SyntaxHighlighter(self.input_edit.document())
        self.output_tabs = QTabWidget()

        self.error_table = QTableWidget()
        self.error_table.setColumnCount(4)
        self.error_table.setHorizontalHeaderLabels(
            [
                "Строка",
                "Позиция",
                "Тип",
                "Сообщение"
            ]
        )
        self.error_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        header = self.error_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.file_watcher = QFileSystemWatcher()
        self._update_file_watcher()

        self.token_table = QTableWidget()
        self.token_table.setColumnCount(5)
        self.token_table.setHorizontalHeaderLabels([
            "Строка",
            "Начало",
            "Конец",
            "Нетерминал",
            "Терминал"
        ])

        self.token_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        header = self.token_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        self.output_tabs.addTab(self.token_table, "Токены")
        self.output_tabs.addTab(self.error_table, "Ошибки")
        self.main_layout.addWidget(self.input_edit)
        self.main_layout.addWidget(self.output_tabs)
        self.input_edit.textChanged.connect(self._handle_text_changed)
        self.model.file_path_changed.connect(self._update_file_watcher)

    def save(self, path):
        try:
            if not path:
                raise ValueError(
                    "Не указан путь для сохранения"
                )

            self._is_saving_internally = True
            if self._is_connected:
                self.file_watcher.fileChanged.disconnect()
                self._is_connected = False

            with open(
                path,
                "w",
                encoding="utf-8"
            ) as f:
                content = self.input_edit.toPlainText()
                if not isinstance(content, str):
                    raise TypeError(
                        "Содержимое должно быть строкой"
                    )
                f.write(content)

            self.model.is_modified = False
            self.last_saved_mtime = os.path.getmtime(path)
            self.file_watcher.addPath(path)
            return True

        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Ошибка сохранения: {str(e)}"
            )
            return False
        finally:
            if not self._is_connected:
                self.file_watcher.fileChanged.connect(
                    self._handle_file_changed
                )
                self._is_connected = True
            self._is_saving_internally = False

    def _update_file_watcher(
        self,
        old_path=None,
        new_path=None
    ):
        if not hasattr(
            self,
            'file_watcher'
        ):
            return

        for path in [old_path, new_path]:
            if path and not isinstance(path, str):
                raise TypeError(
                    "Неверный тип пути"
                )

        if old_path and self.file_watcher.files():
            self.file_watcher.removePath(
                old_path
            )
        if new_path:
            self.file_watcher.addPath(
                new_path
            )

        if self._is_connected:
            self.file_watcher.fileChanged.disconnect()
            self._is_connected = False

        self.file_watcher.fileChanged.connect(
            self._handle_file_changed
        )
        self._is_connected = True

    def _handle_file_changed(self, path):
        if self._is_saving_internally or path != self.model.file_path:
            return

        try:
            current_mtime = os.path.getmtime(path)
        except FileNotFoundError:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Файл был удален"
            )
            return

        if current_mtime == self.last_saved_mtime:
            return

        self._is_reloading = True
        reply = QMessageBox.question(
            self,
            "Изменение файла",
            f"Файл '{os.path.basename(path)}' "
            "изменен извне. "
            "Перезагрузить?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._reload_file()
            self.last_saved_mtime = current_mtime

        self._is_reloading = False

    def _reload_file(self):
        if (
            not self.model.file_path
            or not os.path.exists(
                self.model.file_path
            )
        ):
            QMessageBox.critical(
                self,
                "Ошибка",
                "Файл не существует"
            )
            return

        try:
            with open(
                self.model.file_path,
                "r",
                encoding="utf-8"
            ) as f:
                content = f.read()
            self.input_edit.blockSignals(True)
            self.input_edit.setPlainText(content)
            self.input_edit.blockSignals(False)
            self.model.is_modified = False
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Ошибка загрузки: {str(e)}"
            )

    def _handle_text_changed(self):
        if not self.model.is_modified:
            self.model.is_modified = True


class TabManager(QTabWidget):
    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self._close_tab_handler)
        self._open_files = set()
        self._create_initial_tab()

    def _create_initial_tab(self) -> None:
        self.add_new_tab()

    def add_new_tab(
        self,
        file_path: Optional[str] = None,
        content: str = ""
    ) -> Optional["DocumentWidget"]:
        if file_path:
            if not os.path.exists(file_path):
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Файл не существует"
                )
                return None
            if file_path in self._open_files:
                for i in range(self.count()):
                    widget = self.widget(i)
                    if isinstance(
                        widget,
                        DocumentWidget
                    ) and widget.model.file_path == file_path:
                        self.setCurrentIndex(i)
                        return None

        doc = DocumentWidget(self)
        doc.model.file_path = file_path

        doc.input_edit.blockSignals(True)
        doc.input_edit.setPlainText(content)
        doc.input_edit.blockSignals(False)

        doc.model.modified.connect(
            lambda _, doc=doc: self._update_tab_title(doc)
        )
        doc.model.file_path_changed.connect(
            partial(self._handle_file_path_change, doc)
        )

        title = os.path.basename(
            file_path
        ) if file_path else "Без названия"
        index = self.addTab(
            doc,
            title
        )
        self.setCurrentIndex(index)

        if file_path:
            self._open_files.add(
                file_path
            )
        return doc

    def _handle_file_path_change(
        self,
        doc: "DocumentWidget",
        old_path: Optional[str],
        new_path: Optional[str]
    ) -> None:
        if old_path in self._open_files:
            self._open_files.remove(old_path)
        if new_path:
            self._open_files.add(new_path)
        self._update_tab_title(doc)

    @property
    def parent_window(self) -> "MainWindow":
        parent = self.parent()
        if not isinstance(
            parent,
            MainWindow
        ):
            raise TypeError(
                "Родитель должен быть экземпляром MainWindow"
            )
        return parent

    def _close_tab_handler(
        self,
        index: int
    ) -> None:
        widget = self.widget(index)
        if not isinstance(
            widget,
            DocumentWidget
        ):
            return

        doc = widget
        if doc.model.is_modified:
            reply = QMessageBox.question(
                self,
                "Несохраненные изменения",
                "Сохранить изменения перед закрытием?",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                if not self.parent_window.save_document():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        if doc.model.file_path:
            self._open_files.discard(
                doc.model.file_path
            )
        self.removeTab(index)
        if self.count() == 0:
            self._create_initial_tab()

    def get_current_document(self) -> Optional["DocumentWidget"]:
        widget = self.currentWidget()
        return widget if isinstance(
            widget,
            DocumentWidget
        ) else None

    def _update_tab_title(
        self,
        doc: "DocumentWidget"
    ) -> None:
        index = self.indexOf(doc)
        if index == -1:
            return

        base_name = os.path.basename(
            doc.model.file_path
        ) if doc.model.file_path else "Без названия"
        title = (
            f"{base_name}"
            "{'*' if doc.model.is_modified else ''}"
        )
        self.setTabText(
            index,
            title
        )


class ToolbarManager:
    def __init__(
        self,
        parent: QMainWindow
    ) -> None:
        self.parent = parent
        self.toolbar = QToolBar("Основная панель")
        parent.addToolBar(self.toolbar)

    def add_action(
        self,
        icon_name: str,
        text: str,
        callback: Callable
    ) -> QAction:
        action = QAction(
            QIcon.fromTheme(
                icon_name
            ),
            text,
            self.parent
        )
        action.triggered.connect(callback)
        self.toolbar.addAction(action)
        return action


class MenuManager:
    def __init__(
        self,
        parent: "MainWindow"
    ) -> None:
        self.parent = parent
        self.menu_bar = QMenuBar()
        parent.setMenuBar(self.menu_bar)
        self._setup_menus()

    def _setup_menus(self) -> None:
        self._create_file_menu()
        self._create_edit_menu()
        self._create_text_menu()
        self._create_run_menu()
        self._create_help_menu()

    def _create_file_menu(self) -> None:
        menu = self.menu_bar.addMenu(
            "Файл"
        )
        actions = [
            (
                "Создать",
                "document-new",
                self.parent.new_document
            ),
            (
                "Открыть",
                "document-open",
                self.parent.open_document
            ),
            (
                "Сохранить",
                "document-save",
                self.parent.save_document
            ),
            (
                "Сохранить как",
                "document-save-as",
                self.parent.save_document_as
            ),
            (
                "Выход",
                "application-exit",
                self.parent.close
            ),
        ]
        self._add_menu_actions(
            menu,
            actions
        )

    def _create_edit_menu(self) -> None:
        menu = self.menu_bar.addMenu(
            "Правка"
        )
        actions = [
            (
                "Увеличить шрифт",
                "zoom-in",
                self.parent.increase_font_size
            ),
            (
                "Уменьшить шрифт",
                "zoom-out",
                self.parent.decrease_font_size
            ),
            (
                "Отменить",
                "edit-undo",
                self.parent.undo
            ),
            (
                "Повторить",
                "edit-redo",
                self.parent.redo
            ),
            (
                "Вырезать",
                "edit-cut",
                self.parent.cut
            ),
            (
                "Копировать",
                "edit-copy",
                self.parent.copy
            ),
            (
                "Вставить",
                "edit-paste",
                self.parent.paste
            ),
            (
                "Удалить",
                "edit-delete",
                self.parent.delete
            ),
            (
                "Выделить все",
                "edit-select-all",
                self.parent.select_all
            ),
        ]
        self._add_menu_actions(
            menu,
            actions
        )

    def _create_text_menu(self) -> None:
        menu = self.menu_bar.addMenu(
            "Текст"
        )
        templates = [
            "Постановка задачи",
            "Грамматика",
            "Классификация грамматики",
            "Метод анализа",
            "Диагностика ошибок",
            "Тестовый пример",
            "Библиография",
            "Исходный код",
        ]
        for template in templates:
            action = QAction(
                template,
                self.parent
            )
            action.triggered.connect(
                partial(
                    self.parent.insert_text,
                    template
                )
            )
            menu.addAction(action)

    def _create_run_menu(self) -> None:
        menu = self.menu_bar.addMenu(
            "Выполнение"
        )
        action = QAction(
            "Запустить парсер",
            self.parent
        )
        action.triggered.connect(
            self.parent.run_parser
        )
        menu.addAction(
            action
        )

    def _create_help_menu(self) -> None:
        menu = self.menu_bar.addMenu(
            "Справка"
        )
        actions = [
            (
                "Помощь",
                "help-contents",
                self.parent.show_help
            ),
            (
                "О программе",
                "help-about",
                self.parent.show_about
            ),
        ]
        self._add_menu_actions(
            menu,
            actions
        )

    def _add_menu_actions(self, menu: QMenu, actions: list) -> None:
        for text, icon_name, callback in actions:
            action = QAction(
                QIcon.fromTheme(
                    icon_name
                ),
                text,
                self.parent
            )
            action.triggered.connect(callback)
            menu.addAction(action)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Компилятор")
        self.setGeometry(100, 100, 800, 600)
        self.tab_manager = TabManager(self)
        self.setCentralWidget(self.tab_manager)
        self.menu_manager = MenuManager(self)
        self.toolbar_manager = ToolbarManager(self)
        self._setup_toolbar()
        self._setup_shortcuts()
        self._setup_font_size()
        self.setAcceptDrops(True)
        self.statusBar().showMessage("Готово")

    def _setup_toolbar(self):
        actions = [
            ("document-new", "Новый", self.new_document),
            ("document-open", "Открыть", self.open_document),
            ("document-save", "Сохранить", self.save_document),
            ("edit-undo", "Отменить", self.undo),
            ("edit-redo", "Вернуть", self.redo),
            ("edit-cut", "Вырезать", self.cut),
            ("edit-copy", "Копировать", self.copy),
            ("edit-paste", "Вставить", self.paste),
            ("system-run", "Запуск", self.run_parser),
            ("help-contents", "Справка", self.show_help),
        ]
        for icon, text, callback in actions:
            self.toolbar_manager.add_action(
                icon,
                text,
                callback
            )

    def _setup_shortcuts(self):
        shortcuts = {
            "Ctrl+N": self.new_document,
            "Ctrl+O": self.open_document,
            "Ctrl+S": self.save_document,
            "Ctrl+Shift+S": self.save_document_as,
            "Ctrl+Z": self.undo,
            "Ctrl+Y": self.redo,
            "Ctrl+F": self.run_parser,
            "Ctrl+=": self.increase_font_size,
            "Ctrl+-": self.decrease_font_size,
        }
        for seq, handler in shortcuts.items():
            QShortcut(
                QKeySequence(seq),
                self
            ).activated.connect(handler)

    def _setup_font_size(self):
        self.font_size = 12
        self.update_font_size()

    def update_font_size(self):
        font = QFont()
        font.setPointSize(self.font_size)
        for i in range(self.tab_manager.count()):
            widget = self.tab_manager.widget(i)
            if isinstance(widget, DocumentWidget):
                widget.input_edit.setFont(font)
        self.statusBar().showMessage(
            f"Размер шрифта изменён на {self.font_size}pt",
            3000
        )

    def increase_font_size(self):
        self.font_size += 1
        self.update_font_size()

    def decrease_font_size(self):
        if self.font_size > 1:
            self.font_size -= 1
            self.update_font_size()

    def get_current_doc(self):
        return self.tab_manager.get_current_document()

    def new_document(self):
        self.tab_manager.add_new_tab()
        self.statusBar().showMessage(
            "Создан новый документ",
            5000
        )

    def open_document(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть файл",
            "",
            "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        if path:
            if not os.path.exists(path):
                reply = QMessageBox.question(
                    self,
                    "Файл не найден",
                    "Файл не существует. "
                    "Создать новый?",
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        open(path, "w").close()
                        self.tab_manager.add_new_tab(
                            file_path=path,
                            content=""
                        )
                        self.statusBar().showMessage(
                            f"Открыт файл: {os.path.basename(path)}",
                            5000
                        )
                    except Exception as e:
                        QMessageBox.critical(
                            self,
                            "Ошибка",
                            f"Ошибка создания файла: {str(e)}"
                        )
                        self.statusBar().showMessage(
                            f"Ошибка: {str(e)}",
                            5000
                        )
                else:
                    return
            else:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.tab_manager.add_new_tab(
                        file_path=path,
                        content=content
                    )
                    self.statusBar().showMessage(
                        f"Загружен файл: {os.path.basename(path)}",
                        5000
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Ошибка",
                        f"Ошибка открытия: {str(e)}"
                    )

    def save_document(self):
        self.statusBar().showMessage("Сохранение...")
        if doc := self.tab_manager.get_current_document():
            if doc.model.file_path and doc.save(doc.model.file_path):
                self.tab_manager._update_tab_title(doc)
                self.statusBar().showMessage(
                    "Документ сохранён",
                    5000
                )
                return True
            return self.save_document_as()
        return False

    def save_document_as(self):
        if doc := self.tab_manager.get_current_document():
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить как",
                "",
                "Текстовые файлы (*.txt);;Все файлы (*)"
            )
            if path and doc.save(path):
                doc.model.file_path = path
                self.tab_manager._update_tab_title(doc)
                self.statusBar().showMessage(
                    f"Сохранено в {os.path.basename(path)}",
                    5000
                )
                return True
        return False

    def insert_text(self, text):
        if doc := self.get_current_doc():
            doc.input_edit.insertPlainText(
                f"{text}\n"
            )
            self.statusBar().showMessage(
                "Текст вставлен",
                2000
            )

    def run_parser(self):
        self.statusBar().showMessage("Анализ кода...")
        if doc := self.get_current_doc():
            input_text = doc.input_edit.toPlainText()
            lexer = AdvancedLexer(input_text)
            _, lexer_errors = lexer.lex()
            valid_tokens, validation_errors = lexer.validate_tokens()
            all_errors = lexer_errors + validation_errors

            doc.token_table.setRowCount(0)
            doc.token_table.setRowCount(len(valid_tokens))

            for row, token in enumerate(valid_tokens):
                line = token.line
                start = token.column
                end = start + len(token.value) - 1

                doc.token_table.setItem(row, 0, QTableWidgetItem(str(line)))
                doc.token_table.setItem(row, 1, QTableWidgetItem(str(start)))
                doc.token_table.setItem(row, 2, QTableWidgetItem(str(end)))
                doc.token_table.setItem(row, 3, QTableWidgetItem(token.type))
                doc.token_table.setItem(row, 4, QTableWidgetItem(token.value))

            doc.error_table.setRowCount(0)
            doc.error_table.setHorizontalHeaderLabels(
                [
                    "Строка",
                    "Столбец",
                    "Тип",
                    "Сообщение"
                ]
            )
            doc.error_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            doc.error_table.horizontalHeader().setSectionResizeMode(
                3,
                QHeaderView.ResizeMode.Stretch
            )
            doc.error_table.setSortingEnabled(True)

            for row, error in enumerate(all_errors):
                doc.error_table.insertRow(row)
                doc.error_table.setItem(
                    row,
                    0,
                    QTableWidgetItem(
                        str(error.line)
                    )
                )
                doc.error_table.setItem(
                    row,
                    1,
                    QTableWidgetItem(
                        str(error.column)
                    )
                )
                doc.error_table.setItem(
                    row,
                    2,
                    QTableWidgetItem(
                        "Синтаксическая ошибка"
                    )
                )
                doc.error_table.setItem(
                    row,
                    3,
                    QTableWidgetItem(
                        error.message
                    )
                )

            msg = (
                f"Найдено ошибок: {len(all_errors)}. "
                f"Автоисправлений: {len(validation_errors)}"
                if all_errors else "Анализ завершён успешно"
            )
            self.statusBar().showMessage(
                msg,
                5000
            )

    def undo(self):
        if doc := self.get_current_doc():
            doc.input_edit.undo()
            self.statusBar().showMessage(
                "Действие отменено",
                2000
            )

    def redo(self):
        if doc := self.get_current_doc():
            doc.input_edit.redo()
            self.statusBar().showMessage(
                "Действие возвращено",
                2000
            )

    def cut(self):
        if doc := self.get_current_doc():
            doc.input_edit.cut()
            self.statusBar().showMessage(
                "Текст вырезан",
                2000
            )

    def copy(self):
        if doc := self.get_current_doc():
            doc.input_edit.copy()
            self.statusBar().showMessage(
                "Текст скопирован",
                2000
            )

    def paste(self):
        if doc := self.get_current_doc():
            doc.input_edit.paste()
            self.statusBar().showMessage(
                "Текст вставлен",
                2000
            )

    def delete(self):
        if doc := self.get_current_doc():
            doc.input_edit.textCursor().removeSelectedText()
            self.statusBar().showMessage(
                "Текст удалён",
                2000
            )

    def select_all(self):
        if doc := self.get_current_doc():
            doc.input_edit.selectAll()
            self.statusBar().showMessage(
                "Весь текст выделен",
                2000
            )

    def show_help(self):
        QMessageBox.information(
            self,
            "Справка",
            "Документация приложения",
            QMessageBox.StandardButton.Ok
        )
        self.statusBar().showMessage(
            "Открыта справка",
            3000
        )

    def show_about(self):
        QMessageBox.about(
            self,
            "О программе",
            "Версия 0.1"
        )
        self.statusBar().showMessage(
            "Открыто окно 'О программе'",
            3000
        )

    def closeEvent(self, event):
        for i in range(self.tab_manager.count()):
            widget = self.tab_manager.widget(i)
            if isinstance(widget, DocumentWidget) and widget.model.is_modified:
                name = os.path.basename(
                    widget.model.file_path
                ) if widget.model.file_path else "Без имени"
                reply = QMessageBox.question(
                    self,
                    "Несохранённые изменения",
                    f"Документ '{name}' имеет "
                    "несохранённые изменения. "
                    "Сохранить?",
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                    | QMessageBox.StandardButton.Cancel
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if not self.save_document():
                        event.ignore()
                        return
                elif reply == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return
        event.accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                try:
                    with open(
                        path,
                        "r",
                        encoding="utf-8"
                    ) as f:
                        self.tab_manager.add_new_tab(
                            file_path=path, content=f.read()
                        )
                        self.statusBar().showMessage(
                            f"Открыт файл: {os.path.basename(path)}",
                            5000
                        )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Ошибка",
                        f"Ошибка открытия: {str(e)}"
                    )


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")
    QLocale.setDefault(
        QLocale(
            QLocale.Language.Russian,
            QLocale.Country.Russia
        )
    )
    app = QApplication(sys.argv)
    DarkTheme.apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
