import sys
import os
import json

# --- ИСПРАВЛЕНИЕ ДЛЯ ПЛАГИНА (для PySide6) ---
import PySide6
plugin_path = os.path.join(os.path.dirname(PySide6.__file__), 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
# --- КОНЕЦ ИСПРАВЛЕНИЯ ---

from PySide6 import QtWidgets, QtGui, QtCore
from datetime import datetime, timedelta

# --- КОНСТАНТЫ ПРИЛОЖЕНИЯ И СТИЛЕЙ ---
TASKS_FILE_NAME = "tasks.json"
ABOUT_FILE_NAME = "about.txt"
WINDOW_WIDTH = 300
WINDOW_HEIGHT = 266
ARCHIVE_WIDTH = int(WINDOW_WIDTH)
ARCHIVE_HEIGHT = 400
ABOUT_HEIGHT = 450
MARGIN_BOTTOM = 50
ICON_FILE_NAME = "traytodo.ico"

BG_MAIN_COLOR = "#9ACEEB"
BG_ARCHIVE_COLOR = "#f0e891"
BG_ABOUT_COLOR = "#b0b0b0"
SCROLLBAR_COLOR = "#b08d06"

# (Константы QSS)
LIST_VIEW_INDICATOR_QSS = """
    QCheckBox::indicator {
        width: 12px;
        height: 12px;
    }
    QCheckBox::indicator:unchecked {
        background-color: #ffffff;
        border: 1px solid #777777;
        border-radius: 0px;
    }
    QCheckBox::indicator:unchecked:hover {
        border: 1px solid #333333;
    }
    QCheckBox::indicator:checked {
        background-color: #444444;
        border: 1px solid #777777;
        border-radius: 0px;
    }
    QCheckBox::indicator:checked:hover {
        background-color: #666666;
        border: 1px solid #333333;
        border-radius: 0px;
    }
"""

SCROLLBAR_BASE_QSS = (
    "QScrollBar:vertical{{background:transparent;width:7px;margin:2px 0 2px 0;border-radius:4px;}}"
    "QScrollBar::handle:vertical{{background:{scroll_color};min-height:{min_h}px;max-height:{max_h}px;border-radius:4px;}}"
    "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;background:none;border:none;}}"
    "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{{background:none;}}"
)
# -----------------------------------------------

class TaskWidget(QtWidgets.QWidget):
    task_changed = QtCore.Signal()
    task_deleted = QtCore.Signal(QtWidgets.QWidget) 
    task_edited = QtCore.Signal()

    def __init__(self, task_data, font, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.main_font = font
        
        self.initUI()
        self.update_style()

    def initUI(self):
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 3) 
        self.main_layout.setSpacing(0)
        self.setStyleSheet(f"background-color: {BG_MAIN_COLOR};")

        self.stacked_widget = QtWidgets.QStackedWidget()
        
        self.stacked_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, 
            QtWidgets.QSizePolicy.Policy.Preferred
        )
        
        self.main_layout.addWidget(self.stacked_widget)

        # --- Страница 0: ВИДЖЕТ ПРОСМОТРА (Чекбокс + Текст) ---
        self.view_widget = QtWidgets.QWidget()
        self.view_widget.setStyleSheet("background: transparent; border: none;")
        
        view_layout = QtWidgets.QHBoxLayout(self.view_widget)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(5)

        self.check_box = QtWidgets.QCheckBox()
        self.check_box.setChecked(self.task_data.get("checked", False))
        self.check_box.setStyleSheet(LIST_VIEW_INDICATOR_QSS)
        self.check_box.stateChanged.connect(self.on_check_changed)
        
        checkbox_width = self.check_box.minimumSizeHint().width()
        
        self.label = QtWidgets.QLabel(self.task_data.get("text", ""))
        self.label.setFont(self.main_font)
        self.label.setWordWrap(True)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        self.label.setStyleSheet("margin-top: -3px;") 

        view_layout.addWidget(self.check_box, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        view_layout.addWidget(self.label, 1, QtCore.Qt.AlignmentFlag.AlignTop)
        
        self.stacked_widget.addWidget(self.view_widget)

        # --- Страница 1: ВИДЖЕТ РЕДАКТИРОВАНИЯ (Кружок + QLineEdit) ---
        self.edit_wrapper = QtWidgets.QWidget()
        self.edit_wrapper.setStyleSheet("background: transparent; border: none;")
        
        self.edit_layout = QtWidgets.QHBoxLayout(self.edit_wrapper) 
        self.edit_layout.setContentsMargins(0, 0, 0, 0) 
        self.edit_layout.setSpacing(5)
        
        self.bullet_container = QtWidgets.QWidget()
        self.bullet_container.setFixedSize(checkbox_width, 12) 
        
        bullet_container_layout = QtWidgets.QHBoxLayout(self.bullet_container)
        bullet_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.bullet_label = QtWidgets.QLabel()
        self.bullet_label.setFixedSize(12, 12)
        
        bullet_container_layout.addWidget(self.bullet_label, 0, QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        
        self.edit_layout.addWidget(self.bullet_container, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        
        self.edit_line = QtWidgets.QLineEdit()
        self.edit_line.setFont(self.main_font)
        
        self.edit_layout.addWidget(self.edit_line, 1, QtCore.Qt.AlignmentFlag.AlignTop)
        
        self.stacked_widget.addWidget(self.edit_wrapper)

        # --- Подключения ---
        self.edit_line.returnPressed.connect(self.on_save_edit)
        self.edit_line.editingFinished.connect(self.on_save_edit)
        
        self.view_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.view_widget.customContextMenuRequested.connect(self.show_task_menu)
        
        self.view_widget.mouseDoubleClickEvent = self.on_view_widget_double_clicked

    def update_style(self):
        font = QtGui.QFont(self.main_font)
        font.setStrikeOut(self.task_data.get("checked", False))
        font.setBold(self.task_data.get("important", False))
        self.label.setFont(font)
        
        edit_font = QtGui.QFont(self.main_font)
        edit_font.setBold(self.task_data.get("important", False))
        self.edit_line.setFont(edit_font)

        fm = QtGui.QFontMetrics(edit_font)
        font_height = fm.height()
        
        self.bullet_label.setStyleSheet(
            "background-color: black; border-radius: 6px;"
        )

        self.edit_line.setStyleSheet(
            f"""
            QLineEdit {{
                background: transparent; 
                border: none; 
                border-radius: 0px; 
                
                padding-left: 0px; 
                padding-top: 0px; 
                padding-bottom: 0px; 

                min-height: {font_height}px;
                max-height: {font_height}px;

                /* Оставляем хак для выравнивания текста */
                margin-top: -3px;
            }}
            """
        )

    def on_check_changed(self, state):
        if self.stacked_widget.currentIndex() == 1:
            self.on_save_edit() 
            
        self.task_data["checked"] = (state == QtCore.Qt.CheckState.Checked)
        if self.task_data["checked"]:
            self.task_data["date"] = QtCore.QDate.currentDate().toString("yyyy-MM-dd")
        self.update_style()
        self.task_changed.emit()

    def show_task_menu(self, position):
        if self.stacked_widget.currentIndex() == 1:
            self.on_save_edit()
            
        menu = QtWidgets.QMenu()
        style = self.style()
        
        edit_icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView)
        edit_action = menu.addAction(edit_icon, "Edit")
        
        important_action = QtGui.QAction("Important", menu, checkable=True)
        important_action.setChecked(self.task_data.get("important", False))
        menu.addAction(important_action)

        delete_icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TrashIcon)
        delete_action = menu.addAction(delete_icon, "Delete")

        action = menu.exec(self.view_widget.mapToGlobal(position))
        
        if action == delete_action:
            self.task_deleted.emit(self)
        elif action == edit_action:
            self.on_edit_task()
        elif action == important_action:
            self.task_data["important"] = important_action.isChecked()
            self.update_style()
            self.task_changed.emit()

    def on_view_widget_double_clicked(self, event):
        if self.check_box.geometry().contains(event.position().toPoint()):
            event.ignore()
            return
            
        self.on_edit_task()
        event.accept()

    def on_edit_task(self):
        if self.stacked_widget.currentIndex() == 1:
            return 
            
        # VVVVVVVV (ИЗМЕНЕНИЕ 1) VVVVVVVV
        # "Замораживаем" высоту виджета до того, как покажем QLineEdit
        # (Берем текущую высоту, которая основана на QLabel)
        current_height = self.height()
        # ^^^^^^^^ КОНЕЦ ИЗМЕНЕНИЯ 1 ^^^^^^^^
        
        self.edit_line.setText(self.task_data.get("text", ""))
        
        self.stacked_widget.setCurrentIndex(1)

        # VVVVVVVV (ИЗМЕНЕНИЕ 2) VVVVVVVV
        # Применяем "заморозку"
        self.setFixedHeight(current_height)
        # ^^^^^^^^ КОНЕЦ ИЗМЕНЕНИЯ 2 ^^^^^^^^
        
        self.edit_line.selectAll()
        self.edit_line.setFocus()
        
        # VVVVVVVV (ИЗМЕНЕНИЕ 3) VVVVVVVV
        # Убираем оповещение, чтобы окно не "дергалось"
        # self.task_edited.emit() 
        # ^^^^^^^^ КОНЕЦ ИЗМЕНЕНИЯ 3 ^^^^^^^^


    def on_save_edit(self):
        if self.stacked_widget.currentIndex() == 0:
            return

        new_text = self.edit_line.text().replace("\n", " ").strip()
        current_text = self.task_data.get("text", "")

        text_changed = False
        if new_text and new_text != current_text:
            self.task_data["text"] = new_text
            self.label.setText(new_text)
            text_changed = True
        elif not new_text:
            pass
        
        # VVVVVVVV (ИЗМЕНЕНИЕ 4) VVVVVVVV
        # "Отпускаем" высоту виджета до того, как покажем QLabel
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215) # 16777215 это QWIDGETSIZE_MAX
        # ^^^^^^^^ КОНЕЦ ИЗМЕНЕНИЯ 4 ^^^^^^^^
        
        self.stacked_widget.setCurrentIndex(0)
        
        self.update_style() 
        
        self.adjustSize() 
        
        if text_changed:
            self.task_changed.emit()
        else:
            self.task_edited.emit()
        
    def get_data(self):
        return self.task_data


class ToDoApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.archive_window = None
        self.tray_menu = None
        self.about_win = None
        self.group_by_period = True
        self.tasks_data = {"group_by_period": True, "tasks": []} 
        
        if getattr(sys, 'frozen', False):
            self.internal_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            self.external_dir = os.path.dirname(sys.executable)
        else:
            self.internal_dir = os.path.dirname(os.path.abspath(__file__))
            self.external_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.TASKS_FILE = os.path.join(self.external_dir, TASKS_FILE_NAME)
        self.ABOUT_FILE = os.path.join(self.internal_dir, ABOUT_FILE_NAME)
        self.ICON_FILE = os.path.join(self.internal_dir, ICON_FILE_NAME)
        
        self.initUI()
        self.createTrayIcon()
        self.load_tasks()
        self.update_task_styles() 

        self.current_display_date = QtCore.QDate.currentDate()
        self.date_timer = QtCore.QTimer(self)
        self.date_timer.timeout.connect(self.check_date_change)
        self.date_timer.start(1000)
        
        self.hide()

    def showEvent(self, event):
        super().showEvent(event)
        QtCore.QTimer.singleShot(0, self.adjust_window_height)

    def initUI(self):
        self.font = QtGui.QFont("Verdana", 11)
        self._setup_window()
        self._setup_widgets()
        self._setup_layout()
        self._connect_signals()
        self.update_header()

    def _setup_window(self):
        self.setWindowTitle("TRAYTODO")
        self.setFixedWidth(WINDOW_WIDTH)
        self.setStyleSheet(f"background-color: {BG_MAIN_COLOR}; font-family: Verdana; border-radius: 14px;")
        self.setWindowFlags(QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.FramelessWindowHint)
        if os.path.exists(self.ICON_FILE):
            self.setWindowIcon(QtGui.QIcon(self.ICON_FILE))
        else:
            self.setWindowIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TitleBarShadeButton))

    def _setup_widgets(self):
        self.header = QtWidgets.QLabel(alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self.header.setFont(self.font)
        self.header.setStyleSheet("border: none; font-weight: normal;")

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff) 

        self.tasks_container = QtWidgets.QWidget()
        self.tasks_container.setStyleSheet("background: transparent;")
        
        self.tasks_layout = QtWidgets.QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(0)
        self.tasks_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.tasks_container)

        self.new_task = QtWidgets.QLineEdit(placeholderText="+")
        self.new_task.setFont(self.font)
        self.new_task.setStyleSheet(
            f"QLineEdit {{ background-color: {BG_MAIN_COLOR}; border: none; border-radius: 0px; padding: 5px; }}"
            "QLineEdit:focus { background-color: white; }"
        )

    def _setup_layout(self):
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setSpacing(5)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.addWidget(self.header)
        self.layout.addWidget(self.scroll_area, 1) 
        self.layout.addSpacing(20) 
        self.layout.addWidget(self.new_task)

    def _connect_signals(self):
        self.new_task.returnPressed.connect(self.handle_new_task)

    def check_date_change(self):
        new_date = QtCore.QDate.currentDate()
        if new_date != self.current_display_date:
            self.current_display_date = new_date
            self.update_header()
            self.load_tasks()

    def _clear_tasks_layout(self):
        while self.tasks_layout.count() > 0:
            item = self.tasks_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
    
    def load_tasks(self):
        self._clear_tasks_layout()
        
        if not os.path.exists(self.TASKS_FILE):
            self.tasks_data = {"group_by_period": True, "tasks": []}
            return

        today_str = QtCore.QDate.currentDate().toString("yyyy-MM-dd")
        tasks_modified = False
        
        try:
            with open(self.TASKS_FILE, "r", encoding="utf-8") as f:
                self.tasks_data = json.load(f)
            tasks = self.tasks_data.get("tasks", [])
            self.group_by_period = self.tasks_data.get("group_by_period", True)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.tasks_data = {"group_by_period": True, "tasks": []}
            return

        active_tasks = []
        for task in self.tasks_data.get("tasks", []):
            if task.get("checked", False) and not task.get("archive", False) and task.get("date", today_str) != today_str:
                task["archive"] = True
                tasks_modified = True
            
            if not task.get("archive", False):
                active_tasks.append(task)

        for task_data in active_tasks:
            self.add_task(task_data)
            
        if tasks_modified:
            try:
                with open(self.TASKS_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.tasks_data, f, ensure_ascii=False, indent=2)
            except Exception as e: 
                print(f"Task save error during auto-archive: {e}")
        
    def update_header(self):
        today = QtCore.QDate.currentDate()
        weekday_names = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}
        date_str = today.toString("dd.MM")
        weekday_str = weekday_names[today.dayOfWeek()]
        self.header.setText(f"{date_str}, {weekday_str}")

    def add_task(self, task_data):
        widget = TaskWidget(task_data, self.font)
        
        widget.task_changed.connect(self.on_task_changed)
        widget.task_deleted.connect(self.on_task_deleted)
        widget.task_edited.connect(self.on_task_edited)
        
        self.tasks_layout.addWidget(widget)

    def handle_new_task(self):
        text = self.new_task.text().replace("\n", " ").strip()
        
        if text:
            task_data = {
                "text": text, 
                "checked": False, 
                "archive": False, 
                "date": QtCore.QDate.currentDate().toString("yyyy-MM-dd"),
                "important": False
            }
            self.add_task(task_data)
            self.new_task.clear()
            
            self.on_task_changed()

    def on_task_changed(self):
        self.save_tasks()
        QtCore.QTimer.singleShot(0, self.adjust_window_height)

    def on_task_edited(self):
        QtCore.QTimer.singleShot(0, self.adjust_window_height)
        
    def on_task_deleted(self, widget):
        widget.deleteLater()
        self.save_tasks()
        QtCore.QTimer.singleShot(0, self.adjust_window_height)
        
    def update_task_styles(self):
        pass

    def adjust_window_height(self):
        header_height = self.header.sizeHint().height()
        new_task_height = self.new_task.sizeHint().height()

        margins = self.layout.contentsMargins().top() + self.layout.contentsMargins().bottom()
        spacing_top = self.layout.spacing()
        spacing_bottom = 20 
        
        list_content_height = self.tasks_container.sizeHint().height()

        metrics = QtGui.QFontMetrics(self.font)
        padding = metrics.height() + 5 
        
        # (Возвращаем буфер, т.к. мы убрали "дерганье" другим способом)
        two_line_buffer = metrics.height() * 2

        content_height = (header_height + spacing_top + 
                          list_content_height + 
                          spacing_bottom + new_task_height + 
                          margins + padding +
                          two_line_buffer) 

        final_height = max(content_height, WINDOW_HEIGHT)
        
        screen = QtWidgets.QApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else self.screen().availableGeometry()
        max_height = screen_geom.height() - MARGIN_BOTTOM
        
        if final_height > max_height:
            final_height = max_height
            self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
        self.setFixedHeight(final_height)
        
        bottom_y = screen_geom.bottom() - MARGIN_BOTTOM
        new_y = bottom_y - self.height()
        x = self.x() if self.isVisible() else screen_geom.right() - self.width() - 10
        self.move(x, new_y)

    def save_tasks(self):
        archived_tasks = []
        if self.tasks_data and "tasks" in self.tasks_data:
                 archived_tasks = [t for t in self.tasks_data["tasks"] if t.get("archive", False)]
            
        new_active_tasks = []
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            widget = item.widget()
            if widget and isinstance(widget, TaskWidget):
                new_active_tasks.append(widget.get_data())
            
        self.tasks_data = {
            "group_by_period": self.group_by_period,
            "tasks": new_active_tasks + archived_tasks
        }
        
        try:
            with open(self.TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks_data, f, ensure_ascii=False, indent=2)
        except Exception as e: 
            print(f"Task save error: {e}")
    
    def get_archived_tasks(self):
        if not self.tasks_data or "tasks" not in self.tasks_data:
            return []
            
        return [t for t in self.tasks_data["tasks"] if t.get("archive", False)]

    def createTrayIcon(self):
        self.tray = QtWidgets.QSystemTrayIcon(self)
        if os.path.exists(self.ICON_FILE):
            self.tray.setIcon(QtGui.QIcon(self.ICON_FILE))
        else:
            self.tray.setIcon(self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_TitleBarShadeButton))

        self.tray_menu = QtWidgets.QMenu()
        style = self.style()
        archive_icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirHomeIcon)
        self.action_show_archive = self.tray_menu.addAction(archive_icon, "Show archive")
        self.action_show_archive.triggered.connect(self.on_archive_from_tray)
        self.tray_menu.addSeparator()
        
        info_icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation)
        
        about_action = self.tray_menu.addAction(info_icon, "About")
        about_action.triggered.connect(self.show_about_dialog)
        self.tray_menu.addSeparator()
        exit_icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogCloseButton)
        self.action_exit = self.tray_menu.addAction(exit_icon, "Close")
        self.action_exit.triggered.connect(QtWidgets.QApplication.instance().quit)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.onTrayActivated)
        self.tray.setVisible(True)

    def onTrayActivated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide_main_window()
            else:
                self.show_main_window()

    def show_main_window(self):
        screen = QtWidgets.QApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else self.screen().availableGeometry()
        x = screen_geom.right() - self.width() - 10
        bottom_y = screen_geom.bottom() - MARGIN_BOTTOM
        new_y = bottom_y - self.height()
        self.move(x, new_y)
        self.show(); self.raise_(); self.activateWindow()

    def hide_main_window(self):
        if hasattr(self, "archive_window") and self.archive_window:
            self.archive_window.hide()
        if hasattr(self, "about_win") and self.about_win:
            self.about_win.hide()
        self.hide()

    def _generate_about_html(self, text):
        lines = text.split('\n')
        html_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                html_lines.append("<div><br></div>")
            elif stripped.startswith('-'):
                content = stripped[1:].strip()
                html_lines.append(f"<div style='margin-left:15px;'>• {content}</div>")
            else:
                html_lines.append(f"<div>{stripped}</div>")
        
        return f"<div style='font-family:Verdana;font-size:11px;color:black;text-align:left;'>{''.join(html_lines)}</div>"
    
    def show_about_dialog(self):
        if hasattr(self, "archive_window") and self.archive_window and self.archive_window.isVisible(): self.archive_window.hide()
        about_text = "(about.txt not found)"
        if os.path.exists(self.ABOUT_FILE):
            try:
                with open(self.ABOUT_FILE, "r", encoding="utf-8") as f: about_text = f.read().strip()
            except Exception: about_text = "(error reading about.txt)"
            
        about_html = self._generate_about_html(about_text)
        
        if hasattr(self, "about_win") and self.about_win: self.about_win.close()
        self.about_win = QtWidgets.QWidget()
        self.about_win.setWindowTitle("About")
        self.about_win.setFixedSize(WINDOW_WIDTH, ABOUT_HEIGHT)
        self.about_win.setStyleSheet(f"background-color:{BG_ABOUT_COLOR};border-radius:14px;font-family:Verdana;")
        self.about_win.setWindowFlags(QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.FramelessWindowHint)
        layout = QtWidgets.QVBoxLayout(self.about_win)
        layout.setContentsMargins(10,10,10,10); layout.setSpacing(5)
        header = QtWidgets.QLabel("About", alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        header.setFont(self.font)
        header.setStyleSheet("border:none;font-weight:normal;")
        layout.addWidget(header)
        scroll = QtWidgets.QScrollArea(widgetResizable=True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        label = QtWidgets.QLabel(text=about_html, wordWrap=True, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet("border:none;")
        scroll.setWidget(label)
        layout.addWidget(scroll)
        screen = QtWidgets.QApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else self.screen().availableGeometry()
        self.about_win.move(screen_geom.right()-self.about_win.width()-self.width()-20, screen_geom.bottom()-self.about_win.height()-MARGIN_BOTTOM)
        self.about_win.show(); self.about_win.activateWindow()

    def on_archive_from_tray(self):
        self.show_main_window(); self.show_archive()
        
    def show_archive(self):
        if hasattr(self, "about_win") and self.about_win and self.about_win.isVisible(): self.about_win.hide()
        if not hasattr(self, "archive_window") or not self.archive_window:
            self.archive_window = QtWidgets.QWidget()
            list_widget_style = f"QListWidget::item, QTreeWidget::item {{padding:0px;margin:0px;}} QListWidget, QTreeWidget {{background-color:{BG_ARCHIVE_COLOR};border:none;}}"
            self.archive_window.setStyleSheet(f"background-color:{BG_ARCHIVE_COLOR};border:none;font-family:Verdana;border-radius:14px;")
            self.archive_window.setFixedSize(ARCHIVE_WIDTH, ARCHIVE_HEIGHT)
            self.archive_window.setWindowFlags(QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.FramelessWindowHint)
            self.archive_layout = QtWidgets.QVBoxLayout(self.archive_window)
            self.archive_layout.setContentsMargins(10, 10, 10, 10)
            header = QtWidgets.QLabel("done", alignment=QtCore.Qt.AlignmentFlag.AlignRight, font=self.font)
            header.setStyleSheet("border:none;font-weight:normal;")
            self.archive_layout.addWidget(header)
            self.archive_tree = QtWidgets.QTreeWidget()
            self.archive_tree.setHeaderHidden(True)
            self.archive_tree.setFont(self.font)
            self.archive_tree.setWordWrap(True)
            self.archive_tree.setIndentation(10)
            row_height = self.archive_tree.fontMetrics().height() or 24
            two_tasks = row_height * 2
            
            scrollbar_qss = SCROLLBAR_BASE_QSS.format(scroll_color=SCROLLBAR_COLOR, min_h=two_tasks, max_h=two_tasks*2)
            self.archive_tree.setStyleSheet(list_widget_style + f"QTreeWidget::item:selected{{background-color:{BG_ARCHIVE_COLOR};}}" + scrollbar_qss)
            
            self.archive_tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self.archive_tree.customContextMenuRequested.connect(self.show_archive_menu)
            self.archive_layout.addWidget(self.archive_tree)
            self.archive_list = QtWidgets.QListWidget(font=self.font, wordWrap=True, uniformItemSizes=False)
            self.archive_list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            
            self.archive_list.setStyleSheet(list_widget_style + scrollbar_qss)
            
            self.archive_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self.archive_list.customContextMenuRequested.connect(self.show_archive_menu)
            self.archive_layout.addWidget(self.archive_list)
        self.archive_tree.hide(); self.archive_list.hide()
        screen = QtWidgets.QApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else self.screen().availableGeometry()
        self.archive_window.move(screen_geom.right()-self.archive_window.width()-self.width()-20, screen_geom.bottom()-self.archive_window.height()-MARGIN_BOTTOM)
        self.populate_archive(); self.archive_window.show(); self.archive_window.activateWindow()

    def show_archive_menu(self, position):
        menu = QtWidgets.QMenu()
        action_group = QtGui.QAction("Group by period", menu)
        action_group.setCheckable(True)
        action_group.setChecked(self.group_by_period)
        menu.addAction(action_group)
        action_group.triggered.connect(self.toggle_group_by_period)
        widget = self.sender()
        menu.exec(widget.mapToGlobal(position))

    def toggle_group_by_period(self):
        self.group_by_period = not self.group_by_period
        self.save_tasks(); self.populate_archive()

    def format_date(self, date_str):
        try: return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d"), datetime.strptime(date_str, "%Y-%m-%d")
        except: return date_str, datetime.min

    def populate_archive(self):
        tasks = sorted(self.get_archived_tasks(), key=lambda t: self.format_date(t.get("date", ""))[1], reverse=True)
        
        if self.group_by_period:
            self.archive_list.hide(); self.archive_tree.show(); self.archive_tree.clear()
            
            today = datetime.today().date()
            groups = {
                "Yesterday": [],
                "Last week": [],
                "Last month": [],
                "Older": []
            }
            
            for t in tasks:
                date_str, date_obj_full = self.format_date(t.get("date", ""))
                
                if date_obj_full == datetime.min:
                    groups["Older"].append(t)
                    continue

                date_obj = date_obj_full.date()
                days_ago = (today - date_obj).days

                if days_ago == 1:
                    groups["Yesterday"].append(t)
                elif 1 < days_ago <= 7:
                    groups["Last week"].append(t)
                elif 7 < days_ago <= 30:
                    groups["Last month"].append(t)
                else: 
                    groups["Older"].append(t)

            group_keys = ["Yesterday", "Last week", "Last month", "Older"]
            
            for t in groups["Yesterday"]:
                child = QtWidgets.QTreeWidgetItem(self.archive_tree)
                date_disp = self.format_date(t["date"])[1].strftime("%d.%m")
                child.setText(0, f"{date_disp} - {t['text']}")
                child.setFont(0, self.font); child.setTextAlignment(0, QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
                
            for group_name in group_keys[1:]:
                group_tasks = groups[group_name]
                if not group_tasks: continue
                
                parent = QtWidgets.QTreeWidgetItem(self.archive_tree, [group_name])
                parent.setExpanded(False); parent.setFont(0,self.font); parent.setTextAlignment(0,QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
                
                for t in group_tasks:
                    child = QtWidgets.QTreeWidgetItem(parent)
                    date_disp = self.format_date(t["date"])[1].strftime("%d.%m")
                    child.setText(0, f"{date_disp} - {t['text']}")
                    child.setFont(0, self.font); child.setTextAlignment(0,QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
                    
            if self.archive_tree.topLevelItemCount() > 0 and self.archive_tree.topLevelItem(0):
                self.archive_tree.expandItem(self.archive_tree.topLevelItem(0))

        else:
            self.archive_tree.hide(); self.archive_list.show(); self.archive_list.clear()
            for t in tasks:
                date_disp = self.format_date(t["date"])[1].strftime("%d.%m")
                item = QtWidgets.QListWidgetItem(f"{date_disp} - {t['text']}")
                item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags); item.setFont(0, self.font); item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
                self.archive_list.addItem(item)
    
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False) 
    todo = ToDoApp()
    sys.exit(app.exec())