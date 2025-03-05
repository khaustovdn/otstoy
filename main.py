import os
import sys
import locale
from functools import partial
from typing import Optional
from PySide6.QtCore import (
    QLocale,
    QRegularExpression,
    Qt,
    QSize,
    QRect,
    Signal
)
from PySide6.QtGui import (
    QTextCharFormat,
    QFont,
    QColor,
    QIcon,
    QAction,
    QPainter,
    QKeySequence,
    QSyntaxHighlighter,
    QShortcut
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTextEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QToolBar,
    QMenu,
    QMenuBar,
    QFileDialog,
    QMessageBox
)


class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: Optional[QTextEdit] = None) -> None:
        super().__init__(parent)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(255, 165, 0))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            'if', 'else', 'while', 'for', 'return', 'break',
            'function', 'var', 'let', 'const', 'true', 'false', 'null',
        ]
        for word in keywords:
            pattern = QRegularExpression(
                r'\b' + QRegularExpression.escape(word) + r'\b',
            )
            self.highlighting_rules.append((pattern, keyword_format))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    fmt,
                )


class LineNumberArea(QWidget):
    def __init__(self, editor: 'TextEditor') -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event: 'QPaintEvent') -> None:
        self.editor.line_number_area_paint_event(event)


class TextEditor(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance('9') * digits

    def update_line_number_area_width(self, _: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height())

    def resizeEvent(self, event: 'QResizeEvent') -> None:
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

    def line_number_area_paint_event(self, event: 'QPaintEvent') -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), Qt.GlobalColor.lightGray)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(
            block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(
                    0,
                    int(top),
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1)
                )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1


class DocumentWidget(QWidget):
    modified = Signal(bool)
    file_path_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._file_path: Optional[str] = None
        self._is_modified: bool = False
        self.main_layout = QVBoxLayout(self)

        self.input_edit = TextEditor()
        self.highlighter = SyntaxHighlighter(self.input_edit.document())
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)

        self.main_layout.addWidget(self.input_edit)
        self.main_layout.addWidget(self.output_edit)
        self.input_edit.textChanged.connect(self._handle_text_changed)

    @property
    def file_path(self) -> Optional[str]:
        return self._file_path

    @file_path.setter
    def file_path(self, value: Optional[str]) -> None:
        self._file_path = value
        self.file_path_changed.emit(value if value else "")

    @property
    def is_modified(self) -> bool:
        return self._is_modified

    @is_modified.setter
    def is_modified(self, value: bool) -> None:
        self._is_modified = value
        self.modified.emit(value)

    def _handle_text_changed(self) -> None:
        if not self._is_modified:
            self.is_modified = True


class TabManager(QTabWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self._create_initial_tab()

    def _create_initial_tab(self) -> None:
        self.add_new_tab()

    def add_new_tab(self, file_path: Optional[str] = None, content: str = "") -> DocumentWidget:
        doc = DocumentWidget(self)
        doc.file_path = file_path
        doc.input_edit.setPlainText(content)

        doc.modified.connect(partial(self._update_tab_title, doc))
        doc.file_path_changed.connect(partial(self._update_tab_title, doc))

        title = os.path.basename(file_path) if file_path else "Untitled"
        index = self.addTab(doc, title)
        self.setCurrentIndex(index)
        return doc

    def close_tab(self, index: int) -> None:
        widget = self.widget(index)
        if isinstance(widget, DocumentWidget):
            doc = widget
            if doc.is_modified:
                reply = QMessageBox.question(
                    self,
                    "Несохраненные изменения",
                    "Сохранить изменения перед закрытием?",
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No |
                    QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if not self.parent().save_document():
                        return
                elif reply == QMessageBox.StandardButton.Cancel:
                    return

            self.removeTab(index)
            if self.count() == 0:
                self._create_initial_tab()

    def get_current_document(self) -> Optional[DocumentWidget]:
        widget = self.currentWidget()
        return widget if isinstance(widget, DocumentWidget) else None

    def _update_tab_title(self, doc: DocumentWidget) -> None:
        index = self.indexOf(doc)
        base_name = (
            os.path.basename(doc.file_path) if doc.file_path else "Untitled"
        )
        title = f"{base_name}{'*' if doc.is_modified else ''}"
        self.setTabText(index, title)


class ToolbarManager:
    def __init__(self, parent: QMainWindow) -> None:
        self.parent = parent
        self.toolbar = QToolBar("Main Toolbar")
        parent.addToolBar(self.toolbar)

    def add_action(self, icon_name: str, text: str, callback: callable) -> QAction:
        action = QAction(QIcon.fromTheme(icon_name), text, self.parent)
        action.triggered.connect(callback)
        self.toolbar.addAction(action)
        return action


class MenuManager:
    def __init__(self, parent: QMainWindow) -> None:
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
        menu = self.menu_bar.addMenu("Файл")
        actions = [
            ("Создать", "document-new", self.parent.new_document),
            ("Открыть", "document-open", self.parent.open_document),
            ("Сохранить", "document-save", self.parent.save_document),
            (
                "Сохранить как",
                "document-save-as",
                self.parent.save_document_as,
            ),
            ("Выход", "application-exit", self.parent.close),
        ]
        self._add_menu_actions(menu, actions)

    def _create_edit_menu(self) -> None:
        menu = self.menu_bar.addMenu("Правка")
        actions = [
            ("Увеличить шрифт", "zoom-in", self.parent.increase_font_size),
            ("Уменьшить шрифт", "zoom-out", self.parent.decrease_font_size),
            ("Отменить", "edit-undo", self.parent.undo),
            ("Повторить", "edit-redo", self.parent.redo),
            ("Вырезать", "edit-cut", self.parent.cut),
            ("Копировать", "edit-copy", self.parent.copy),
            ("Вставить", "edit-paste", self.parent.paste),
            ("Удалить", "edit-delete", self.parent.delete),
            ("Выделить все", "edit-select-all", self.parent.select_all),
        ]
        self._add_menu_actions(menu, actions)

    def _create_text_menu(self) -> None:
        menu = self.menu_bar.addMenu("Текст")
        templates = [
            "Постановка задачи",
            "Грамматика",
            "Классификация грамматики",
            "Метод анализа",
            "Диагностика и нейтрализация ошибок",
            "Тестовый пример",
            "Список литературы",
            "Исходный код программы",
        ]
        for template in templates:
            action = QAction(template, self.parent)
            action.triggered.connect(
                partial(self.parent.insert_text, template),
            )
            menu.addAction(action)

    def _create_run_menu(self) -> None:
        menu = self.menu_bar.addMenu("Пуск")
        action = QAction("Запустить анализатор", self.parent)
        action.triggered.connect(self.parent.run_parser)
        menu.addAction(action)

    def _create_help_menu(self) -> None:
        menu = self.menu_bar.addMenu("Справка")
        actions = [
            ("Вызов справки", "help-contents", self.parent.show_help),
            ("О программе", "help-about", self.parent.show_about),
        ]
        self._add_menu_actions(menu, actions)

    def _add_menu_actions(self, menu: QMenu, actions: list) -> None:
        for text, icon_name, callback in actions:
            action = QAction(QIcon.fromTheme(icon_name), text, self.parent)
            action.triggered.connect(callback)
            menu.addAction(action)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Компилятор")
        self.setGeometry(100, 100, 800, 600)

        self.tab_manager = TabManager()
        self.setCentralWidget(self.tab_manager)
        self.menu_manager = MenuManager(self)
        self.toolbar_manager = ToolbarManager(self)

        self._setup_toolbar()
        self._setup_shortcuts()
        self._setup_font_size()
        self.setAcceptDrops(True)
        self.statusBar().showMessage("Готово")

    def _setup_toolbar(self) -> None:
        actions = [
            ("document-new", "Создать", self.new_document),
            ("document-open", "Открыть", self.open_document),
            ("document-save", "Сохранить", self.save_document),
            ("edit-undo", "Отменить", self.undo),
            ("edit-redo", "Повторить", self.redo),
            ("edit-cut", "Вырезать", self.cut),
            ("edit-copy", "Копировать", self.copy),
            ("edit-paste", "Вставить", self.paste),
            ("system-run", "Запустить анализатор", self.run_parser),
            ("help-contents", "Справка", self.show_help),
        ]
        for icon, text, callback in actions:
            self.toolbar_manager.add_action(icon, text, callback)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+N"),
                  self).activated.connect(self.new_document)
        QShortcut(QKeySequence("Ctrl+O"),
                  self).activated.connect(self.open_document)
        QShortcut(QKeySequence("Ctrl+S"),
                  self).activated.connect(self.save_document)
        QShortcut(QKeySequence("Ctrl+Shift+S"),
                  self).activated.connect(self.save_document_as)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.redo)
        QShortcut(QKeySequence("Ctrl+F"),
                  self).activated.connect(self.run_parser)
        QShortcut(QKeySequence("Ctrl+="),
                  self).activated.connect(self.increase_font_size)
        QShortcut(QKeySequence("Ctrl+-"),
                  self).activated.connect(self.decrease_font_size)

    def _setup_font_size(self) -> None:
        self.font_size = 12
        self.update_font_size()

    def update_font_size(self) -> None:
        font = QFont()
        font.setPointSize(self.font_size)
        for i in range(self.tab_manager.count()):
            widget = self.tab_manager.widget(i)
            if isinstance(widget, DocumentWidget):
                widget.input_edit.setFont(font)
                widget.output_edit.setFont(font)

    def increase_font_size(self) -> None:
        self.font_size += 1
        self.update_font_size()

    def decrease_font_size(self) -> None:
        if self.font_size > 1:
            self.font_size -= 1
            self.update_font_size()

    def get_current_doc(self) -> Optional[DocumentWidget]:
        return self.tab_manager.get_current_document()

    def new_document(self) -> None:
        self.tab_manager.add_new_tab()

    def open_document(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть файл",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            if not os.path.exists(path):
                reply = QMessageBox.question(
                    self,
                    "Файл не найден",
                    "Файл не существует. Хотите создать новый файл?",
                    QMessageBox.StandardButton.Yes |
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        with open(path, 'w', encoding='utf-8') as f:
                            pass
                        self.tab_manager.add_new_tab(
                            file_path=path,
                            content="",
                        )
                    except Exception as e:
                        QMessageBox.critical(
                            self,
                            "Ошибка",
                            f"Не удалось создать файл: {str(e)}",
                        )
                        return
                else:
                    return
            else:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    self.tab_manager.add_new_tab(
                        file_path=path,
                        content=content,
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Ошибка",
                        f"Ошибка открытия файла:\n{str(e)}",
                    )

    def save_document(self) -> bool:
        doc = self.get_current_doc()
        if not doc:
            return False

        if doc.file_path:
            return self._save_to_file(
                doc.file_path,
                doc.input_edit.toPlainText(),
            )
        return self.save_document_as()

    def save_document_as(self) -> bool:
        doc = self.get_current_doc()
        if not doc:
            return False

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить как",
            "",
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            success = self._save_to_file(
                path,
                doc.input_edit.toPlainText(),
            )
            if success:
                doc.file_path = path
                doc.is_modified = False
            return success
        return False

    def _save_to_file(self, path: str, content: str) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Ошибка сохранения файла:\n{str(e)}",
            )
            return False

    def insert_text(self, text: str) -> None:
        if doc := self.get_current_doc():
            doc.input_edit.insertPlainText(f"{text}\n")

    def run_parser(self) -> None:
        if doc := self.get_current_doc():
            input_text = doc.input_edit.toPlainText()
            processed = input_text.upper()  # Заглушка для примера
            doc.output_edit.setPlainText(processed)

    def undo(self) -> None:
        if doc := self.get_current_doc():
            doc.input_edit.undo()

    def redo(self) -> None:
        if doc := self.get_current_doc():
            doc.input_edit.redo()

    def cut(self) -> None:
        if doc := self.get_current_doc():
            doc.input_edit.cut()

    def copy(self) -> None:
        if doc := self.get_current_doc():
            doc.input_edit.copy()

    def paste(self) -> None:
        if doc := self.get_current_doc():
            doc.input_edit.paste()

    def delete(self) -> None:
        if doc := self.get_current_doc():
            doc.input_edit.textCursor().removeSelectedText()

    def select_all(self) -> None:
        if doc := self.get_current_doc():
            doc.input_edit.selectAll()

    def show_help(self) -> None:
        help_text = "Справка"
        QMessageBox.information(self, "Справка", help_text)

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "О программе",
            "Компилятор версия 0.1",
        )

    def closeEvent(self, event) -> None:
        for i in range(self.tab_manager.count()):
            widget = self.tab_manager.widget(i)
            if isinstance(widget, DocumentWidget):
                doc = widget
                if doc.is_modified:
                    reply = QMessageBox.question(
                        self,
                        "Несохраненные изменения",
                        f"Документ '{os.path.basename(
                            doc.file_path)}' имеет несохраненные изменения. Хотите сохранить?"
                        if doc.file_path
                        else "Документ 'Untitled' имеет несохраненные изменения. Хотите сохранить?",
                        QMessageBox.StandardButton.Yes |
                        QMessageBox.StandardButton.No |
                        QMessageBox.StandardButton.Cancel,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        if not self.save_document():
                            event.ignore()
                            return
                    elif reply == QMessageBox.StandardButton.Cancel:
                        event.ignore()
                        return
        event.accept()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        self.tab_manager.add_new_tab(
                            file_path=file_path, content=content)
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Ошибка",
                        f"Ошибка открытия файла:\n{str(e)}",
                    )


if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
    QLocale.setDefault(
        QLocale(QLocale.Language.Russian, QLocale.Country.Russia))

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
