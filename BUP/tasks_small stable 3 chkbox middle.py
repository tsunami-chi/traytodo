import sys
import os
import json
import uuid
from PySide6 import QtWidgets, QtGui, QtCore
from datetime import datetime, timedelta

# --- ИСПРАВЛЕНИЕ ДЛЯ ПЛАГИНА (для PySide6) ---
import PySide6
plugin_path = os.path.join(os.path.dirname(PySide6.__file__), 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
# --- КОНЕЦ ИСПРАВЛЕНИЯ ---


try:
    SCRIPT_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd()

TASKS_FILE = os.path.join(SCRIPT_DIR, "tasks_small.json")

GLOBAL_FONT_SIZE = 11
GLOBAL_TEXT_COLOR = "#555"
CHECKBOX_SIZE = 10 

class ArchiveWindow(QtWidgets.QWidget):
    """Новое окно для показа архива"""
    
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app  # Ссылка на главное окно (SimpleTodo)
        
        # Получаем глобальный шрифт
        self.app_font = QtWidgets.QApplication.font()
        self.app_font.setPointSize(GLOBAL_FONT_SIZE)
        
        self.initUI()
        self.load_archive()

    def initUI(self):
        self.setWindowTitle("Archive")
        self.setFixedSize(275, 350) 
        
        self.setWindowFlags(QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.base_widget = QtWidgets.QWidget(self)
        self.base_widget.setGeometry(self.rect())
        
        self.base_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #f0e891; 
                border-radius: 0px; 
            }}
            QTreeWidget {{
                background-color: transparent;
                border: none;
                color: {GLOBAL_TEXT_COLOR}; 
                outline: 0px; 
            }}
            QTreeWidget::item:selected {{
                background-color: transparent; 
                color: {GLOBAL_TEXT_COLOR}; 
            }}
            QTreeWidget::item:focus {{
                border: none;
                outline: none;
            }}
            
            /* Стилизация скроллбара */
            QScrollBar:vertical {{
                border: none;
                background: #f0e891; /* Фон скроллбара (как у окна) */
                width: 5px;          /* Узкая ширина */
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #D4CC7D; /* Цвет ползунка (чуть темнее) */
                min-height: 20px;
                border-radius: 0px; /* Убираем скругление */
            }}
            /* Убираем кнопки-стрелки */
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QtGui.QColor(0, 0, 0, 100))
        self.base_widget.setGraphicsEffect(shadow)
        
        self.layout = QtWidgets.QVBoxLayout(self.base_widget)  
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.title_label = QtWidgets.QLabel("done")
        self.title_label.setFont(self.app_font) 
        self.title_label.setStyleSheet(f"""
            font-weight: normal; 
            color: {GLOBAL_TEXT_COLOR}; 
            padding-right: 2px;
        """)
        
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop)
        self.layout.addWidget(self.title_label) 
        
        self.list_widget = QtWidgets.QTreeWidget()
        
        self.list_widget.setFont(self.app_font) 
        
        self.list_widget.setHeaderHidden(True)
        self.list_widget.setWordWrap(True)
        self.list_widget.setIndentation(5) # Отступ

        self.layout.addWidget(self.list_widget) 
        
        self.list_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_archive_menu)

    def style_header_item(self, item):
        """Стилизует родительский элемент (заголовок)"""
        font = item.font(0)
        font.setBold(False)                  # Убираем жирность
        font.setPointSize(GLOBAL_FONT_SIZE - 1) # Делаем шрифт меньше (10)
        item.setFont(0, font)
        
        item.setForeground(0, QtGui.QColor(GLOBAL_TEXT_COLOR))
        item.setExpanded(True) 
        
    def load_archive(self):
        """Читает файл, сортирует, группирует по датам и показывает в QTreeWidget"""
        print("ArchiveWindow: Loading grouped archive...")
        self.list_widget.clear()
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        
        tasks_list = self.main_app.read_tasks()
        archived_tasks = [t for t in tasks_list if t.get("archive", False)]
        
        archived_tasks.sort(key=lambda x: x.get("date", "0000-01-01"), reverse=True)
        
        headers = {}

        for task in archived_tasks:
            task_text = task.get("text", "---")
            task_id = task.get("id")
            task_date_str = task.get("date")

            task_date = None
            if task_date_str:
                try:
                    task_date = datetime.fromisoformat(task_date_str).date()
                except ValueError:
                    task_date = None 

            category_key = ""
            category_name = ""
            
            if task_date == today:
                category_key = "today"
                category_name = "Сегодня"
            elif task_date == yesterday:
                category_key = "yesterday"
                category_name = "Вчера"
            elif task_date and task_date >= start_of_week:
                category_key = "week"
                category_name = "На этой неделе"
            elif task_date and task_date >= start_of_month:
                category_key = "month"
                category_name = "В этом месяце"
            else:
                category_key = "later"
                category_name = "Позднее"

            if category_key not in headers:
                header_item = QtWidgets.QTreeWidgetItem(self.list_widget, [category_name])
                self.style_header_item(header_item)
                headers[category_key] = header_item 
            
            parent_header = headers[category_key]

            task_item = QtWidgets.QTreeWidgetItem(parent_header, [f"• {task_text}"])
            task_item.setData(0, QtCore.Qt.UserRole, task_id) 
            
    def show_archive_menu(self, position):
        """Меню для удаления"""
        
        item = self.list_widget.itemAt(position)
        if not item:
            return
            
        task_id = item.data(0, QtCore.Qt.UserRole)
        if not task_id:
            return

        menu = QtWidgets.QMenu()
        
        delete_action = menu.addAction("Delete permanently")
        
        action = menu.exec(self.list_widget.mapToGlobal(position))
        
        if action == delete_action:
            self.main_app.delete_task(task_id)

    def show_and_position(self):
        """Показывает окно СЛЕВА от главного, ВЫРАВНИВАЯ ПО НИЖНЕМU КРАЮ"""
        main_window_geom = self.main_app.geometry()
        main_x = main_window_geom.x()
        main_y = main_window_geom.y()
        main_height = main_window_geom.height()
        
        margin = 10
        new_x = main_x - self.width() - margin
        
        # Окно архива всегда привязано к НИЗУ главного окна.
        new_y = (main_y + main_height) - self.height()
        
        self.move(new_x, new_y)
        self.show()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()


class SimpleTodo(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        self.archive_window = None
        
        self.app_font = QtWidgets.QApplication.font()
        self.app_font.setPointSize(GLOBAL_FONT_SIZE)
        
        self.current_display_date = datetime.now().date()
        
        self.date_timer = QtCore.QTimer(self)
        self.date_timer.timeout.connect(self.check_date_change)
        self.date_timer.start(60000) # Проверка каждую минуту
        
        print("############################################################")
        print(f"### Using data file: {TASKS_FILE}")
        print("############################################################")

        self.initUI()
        self.create_tray_icon()
        self.load_tasks()
        
        self.setWindowFlags(QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)


    def initUI(self):
        self.setWindowTitle("Simple Todo")
        
        self.setFixedWidth(275)  
        self.min_height = 350
        
        # Получаем максимальную высоту на основе экрана
        screen = QtWidgets.QApplication.primaryScreen()
        if not screen:
            screen = self.screen()
            
        self.max_height = screen.availableGeometry().height()
        
        # Устанавливаем начальную высоту
        self.setFixedHeight(self.min_height) 
        
        # "главный" layout для self (прозрачного)
        self.main_container_layout = QtWidgets.QVBoxLayout(self)
        self.main_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.base_widget = QtWidgets.QWidget() # "синий" виджет
        
        self.base_widget.setStyleSheet("""
            QWidget {
                background-color: #9ACEEB;
                border-radius: 0px;
            }
        """)
        
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QtGui.QColor(0, 0, 0, 100))
        self.base_widget.setGraphicsEffect(shadow)
        
        # "внутренний" layout (с отступами) для base_widget
        self.layout = QtWidgets.QVBoxLayout(self.base_widget)  
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        self.title_label = QtWidgets.QLabel("...") 
        self.title_label.setFont(self.app_font) 
        self.title_label.setStyleSheet(f"""
            font-weight: normal; 
            color: {GLOBAL_TEXT_COLOR}; 
            padding-right: 2px;
        """)
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop)
        self.layout.addWidget(self.title_label) 
        
        self.update_header() 
        
        self.list_widget = QtWidgets.QListWidget()
        
        self.list_widget.setFont(self.app_font) 
        
        self.list_widget.setWordWrap(True)

        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                color: {GLOBAL_TEXT_COLOR};
                background-color: transparent; /* Фон списка прозрачный */
                border: none;
                outline: 0px; /* Убирает рамку фокуса */
            }}
            QListWidget::item:selected {{
                background-color: transparent; /* Убирает фон выделения */
                color: {GLOBAL_TEXT_COLOR}; /* Оставляет обычный цвет текста */
            }}
            QListWidget::item:focus {{
                 border: none;
                 outline: none;
            }}
            
            /* VVVVVV (ИЗМЕНЕНИЕ: Убран border) VVVVVV */
            QListWidget QLineEdit {{
                background-color: white;
                border: none; 
                border-radius: 0px;
                padding: 2px;
                color: {GLOBAL_TEXT_COLOR};
            }}
            /* ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ */
            
            QListWidget::indicator {{
                width: {CHECKBOX_SIZE}px;
                height: {CHECKBOX_SIZE}px;
                border: 1px solid {GLOBAL_TEXT_COLOR}; 
                border-radius: 0px; 
            }}
            QListWidget::indicator:unchecked {{
                background-color: #FFFFFF; 
            }}
            QListWidget::indicator:checked {{
                background-color: {GLOBAL_TEXT_COLOR}; 
                border: 1px solid {GLOBAL_TEXT_COLOR}; 
            }}
            
            /* Стилизация скроллбара (аналогично архиву) */
            QScrollBar:vertical {{
                border: none;
                background: #9ACEEB; /* Фон скроллбара (как у окна) */
                width: 5px;          /* Узкая ширина */
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #83B7D0; /* Цвет ползунка (чуть темнее) */
                min-height: 20px;
                border-radius: 0px; /* Убираем скругление */
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        self.input_field = QtWidgets.QLineEdit()
        
        self.input_field.setPlaceholderText("+")
        self.input_field.setFont(self.app_font) 
        self.input_field.setStyleSheet(f"""
            background-color: #FFFFFF; 
            border: none; 
            border-radius: 0px;
            padding: 3px; 
            color: {GLOBAL_TEXT_COLOR}; 
        """)
        
        self.layout.addWidget(self.list_widget)
        self.layout.addWidget(self.input_field)
        
        # Добавляем "синий" виджет в "главный" layout
        self.main_container_layout.addWidget(self.base_widget)
        
        self.input_field.returnPressed.connect(self.add_task)
        
        self.list_widget.itemChanged.connect(self.on_item_changed)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        self.list_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_main_list_menu)

    def resize_window_to_content(self):
        """Пересчитывает высоту окна на основе контента"""
        
        # 1. Рассчитываем высоту "не-списка" (заголовок, поле ввода, отступы)
        non_list_height = 0
        non_list_height += self.title_label.sizeHint().height()
        non_list_height += self.input_field.sizeHint().height()
        
        margins = self.layout.contentsMargins()
        non_list_height += margins.top() + margins.bottom()
        
        non_list_height += self.layout.spacing() * 2 

        # 2. Рассчитываем высоту контента списка
        list_content_height = 0
        count = self.list_widget.count()
        
        if count == 0:
            list_content_height = 20 
        else:
            last_item = self.list_widget.item(count - 1)
            rect = self.list_widget.visualItemRect(last_item)
            list_content_height = rect.y() + rect.height()
            list_content_height += self.list_widget.frameWidth() * 2 

        # 3. Считаем и "зажимаем" (clamp) итоговую высоту
        
        total_content_height = non_list_height + list_content_height
        
        final_height = total_content_height
        
        if final_height < self.min_height:
            final_height = self.min_height
            
        if final_height > self.max_height:
            final_height = self.max_height
            
        # 4. Применяем высоту и корректируем позицию Y
        
        old_height = self.height()
        
        if old_height == final_height:
            return 

        self.setFixedHeight(final_height)
        
        if self.isVisible():
            current_pos = self.pos()
            new_y = current_pos.y() - (final_height - old_height)
            self.move(current_pos.x(), new_y)
            
            if self.archive_window and self.archive_window.isVisible():
                self.archive_window.show_and_position()

    def update_header(self):
        """Обновляет заголовок с датой (вызывается при запуске и в 00:00)"""
        weekdays_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        date_str = self.current_display_date.strftime("%d.%m")
        day_str = weekdays_en[self.current_display_date.weekday()]
        date_title = f"{date_str}, {day_str}"
        self.title_label.setText(date_title)

    def check_date_change(self):
        """Вызывается таймером каждую минуту."""
        new_date = datetime.now().date()
        
        if new_date != self.current_display_date:
            print(f"--- Обнаружена смена даты! {self.current_display_date} -> {new_date} ---")
            
            yesterday_date_iso = self.current_display_date.isoformat()
            
            self.current_display_date = new_date
            self.update_header()
            
            self.run_midnight_archive(yesterday_date_iso)

    def run_midnight_archive(self, yesterday_date_iso):
        """Архивирует выполненные таски, устанавливая вчерашнюю дату."""
        print(f"Запуск авто-архивации. Установка даты на: {yesterday_date_iso}")
        
        tasks_list = self.read_tasks()
        tasks_changed = False
        
        for task in tasks_list:
            if task.get("checked") and not task.get("archive", False):
                task["archive"] = True
                task["date"] = yesterday_date_iso 
                tasks_changed = True
                print(f" -> Авто-архивация таска {task.get('id')[:4]}...")

        if tasks_changed:
            print("Сохранение архивированных тасков...")
            self.write_tasks(tasks_list)
            self.load_tasks() 
        else:
            print("Нет тасков для авто-архивации.")

    def read_tasks(self):
        """Просто читает файл и возвращает список [..]"""
        if not os.path.exists(TASKS_FILE):
            return []  
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            print(f"Error reading {TASKS_FILE}. File will be overwritten.")
            return []

    def write_tasks(self, tasks_list):
        """Просто перезаписывает файл списком [..]"""
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(tasks_list, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved {len(tasks_list)} tasks to {TASKS_FILE}")
        except Exception as e:
            print(f"---!!! CRITICAL WRITE ERROR in {TASKS_FILE} !!!---")
            print(f"---!!! Error: {e} !!!---")

    def load_tasks(self):
        """Читает файл и "рисует" QListWidget (ТОЛЬКО НЕ АРХИВНЫЕ)"""
        
        print("Loading tasks...")
        
        tasks_list = self.read_tasks() 
        
        self.list_widget.blockSignals(True)
        
        self.list_widget.clear()
        
        active_tasks = [t for t in tasks_list if not t.get("archive", False)]
        
        for task in active_tasks: 
            item = QtWidgets.QListWidgetItem(task.get("text", "---"))
            
            font = item.font() 
            
            if task.get("important", False):
                font.setBold(True)
            
            if task.get("checked", False):
                font.setStrikeOut(True)
                
            item.setFont(font) 
            
            item.setFlags(
                item.flags() | 
                QtCore.Qt.ItemFlag.ItemIsUserCheckable |
                QtCore.Qt.ItemFlag.ItemIsEditable 
            )
            
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            
            if task.get("checked", False):
                item.setCheckState(QtCore.Qt.CheckState.Checked)
            else:
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            
            item.setData(QtCore.Qt.UserRole, task.get("id"))
            self.list_widget.addItem(item)
            
        self.list_widget.blockSignals(False)
        
        if self.archive_window and self.archive_window.isVisible():
            self.archive_window.load_archive()

        # Вызов пересчета высоты
        self.resize_window_to_content()


    def add_task(self):
        """Добавляет новый таск"""
        text = self.input_field.text().strip()
        if not text:
            return

        new_task = {
            "id": str(uuid.uuid4()),
            "text": text,
            "date": datetime.now().date().isoformat(), 
            "checked": False,
            "archive": False,
            "important": False 
        }
        
        tasks_list = self.read_tasks()
        tasks_list.append(new_task)
        self.write_tasks(tasks_list)
        
        self.load_tasks() 
        self.input_field.clear()

    def on_item_changed(self, item):
        """Срабатывает, когда мы ставим/убираем галочку ИЛИ заканчиваем редактирование."""
        
        task_id = item.data(QtCore.Qt.UserRole)
        if not task_id:
            return

        tasks_list = self.read_tasks()
        task_to_update = next((t for t in tasks_list if t.get("id") == task_id), None)
        if not task_to_update:
            return

        new_text = item.text().strip()
        new_checked = (item.checkState() == QtCore.Qt.CheckState.Checked)

        current_text = task_to_update.get("text")
        current_checked = task_to_update.get("checked", False)

        data_changed = False
        reload_needed = False

        if new_text != current_text and new_text:
            print(f"Updating text for task ID {task_id[:4]}...")
            task_to_update["text"] = new_text
            data_changed = True
            
            # Нужен пересчет высоты, но без полной перезагрузки
            reload_needed = False
            self.resize_window_to_content() 

        elif not new_text:
            self.list_widget.blockSignals(True)
            item.setText(current_text) 
            self.list_widget.blockSignals(False)
            
        if new_checked != current_checked:
            print(f"Updating check state for task ID {task_id[:4]}...")
            task_to_update["checked"] = new_checked
            data_changed = True
            reload_needed = True # Перезагрузка НУЖНА (для зачеркивания)

        if data_changed:
            self.write_tasks(tasks_list)
            if reload_needed:
                self.load_tasks() 

    def on_item_double_clicked(self, item):
        """Срабатывает по дабл-клику на элементе списка."""
        self.list_widget.editItem(item)

    def show_main_list_menu(self, position):
        """Меню для удаления и важности"""
        item = self.list_widget.itemAt(position)
        if not item:
            return
        
        task_id = item.data(QtCore.Qt.UserRole)
        if not task_id:
            return
            
        
        tasks_list = self.read_tasks()
        current_task = next((t for t in tasks_list if t.get("id") == task_id), None)
        if not current_task:
            return 
            
        is_important = current_task.get("important", False)

        menu = QtWidgets.QMenu()
        
        # 1. Edit
        edit_icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
        edit_action = menu.addAction(edit_icon, "Edit")
        
        # 2. Important
        important_action = menu.addAction("Important") 
        important_action.setCheckable(True)
        important_action.setChecked(is_important)
        
        # 3. Delete
        delete_icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogCloseButton)
        delete_action = menu.addAction(delete_icon, "Delete") 
        
        # 4. Разделитель
        menu.addSeparator()
        
        # 5. Archive all done
        archive_all_icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton) 
        archive_all_action = menu.addAction(archive_all_icon, "Archive all done")
        
        
        action = menu.exec(self.list_widget.mapToGlobal(position))
        
        if action == delete_action:
            self.delete_task(task_id)
        elif action == important_action:
            self.toggle_important(task_id)
        elif action == edit_action:
            self.list_widget.editItem(item)
        elif action == archive_all_action:
            self.archive_all_done_tasks() 
    
    def toggle_important(self, task_id):
        """Переключает статус 'important' для таска"""
        print(f"Toggling 'important' for task {task_id[:4]}...")
        tasks_list = self.read_tasks()
        
        task_found = False
        for task in tasks_list:
            if task.get("id") == task_id:
                task["important"] = not task.get("important", False) 
                task_found = True
                break
        
        if task_found:
            self.write_tasks(tasks_list)
            self.load_tasks() 
        else:
            print(f"Error: Could not find {task_id} to toggle important.")


    def delete_task(self, task_id):
        """Полностью удаляет таск из файла"""
        print(f"Deleting task {task_id[:4]}...")
        tasks_list = self.read_tasks()
        
        new_tasks_list = [t for t in tasks_list if t.get("id") != task_id]
        
        if len(new_tasks_list) < len(tasks_list):
            self.write_tasks(new_tasks_list)
            self.load_tasks() 
        else:
            print(f"Error: Could not find {task_id} to delete.")

    def archive_all_done_tasks(self):
        """Перемещает все 'checked' таски в архив"""
        print("Running 'Archive all done'...")
        tasks_list = self.read_tasks()
        tasks_changed = False
        
        today_date_iso = datetime.now().date().isoformat()
        
        for task in tasks_list:
            # Ищем все, что "checked" и "not archive"
            if task.get("checked") and not task.get("archive", False):
                task["archive"] = True
                task["date"] = today_date_iso 
                tasks_changed = True
                print(f" -> Archiving task {task.get('id')[:4]}...")

        if tasks_changed:
            print("Saving changes and refreshing lists...")
            self.write_tasks(tasks_list)
            self.load_tasks() # Обновляем, чтобы они исчезли
        else:
            print("No 'done' tasks to archive.")

    def create_tray_icon(self):
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        
        # Пытаемся загрузить traytodo.ico
        icon_path = os.path.join(SCRIPT_DIR, "traytodo.ico")
        
        if os.path.exists(icon_path):
            print(f"Loading custom icon from: {icon_path}")
            icon = QtGui.QIcon(icon_path)
        else:
            # Если не нашли, используем стандартную "Yes" (галочку)
            print(f"Warning: traytodo.ico not found at {icon_path}.")
            print("Falling back to default system icon.")
            icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogYesButton)
        
        self.tray_icon.setIcon(icon)
        self.tray_icon.setVisible(True)
        
        self.tray_menu = QtWidgets.QMenu()
        
        # Иконка дискеты Save для Archive
        archive_icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton)
        archive_action = self.tray_menu.addAction(archive_icon, "Archive")
        archive_action.triggered.connect(self.show_archive_window)  
        
        self.tray_menu.addSeparator()
        
        exit_icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogCloseButton)
        exit_action = self.tray_menu.addAction(exit_icon, "Exit")
        
        exit_action.triggered.connect(QtWidgets.QApplication.instance().quit)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        
        self.tray_icon.activated.connect(self.on_tray_clicked)

    def show_archive_window(self):
        """Создает (если нет) и показывает окно архива"""
        if not self.archive_window:
            self.archive_window = ArchiveWindow(self)
        
        if not self.isVisible():
            self.show_and_position()
        
        self.archive_window.load_archive()  
        self.archive_window.show_and_position()


    def show_and_position(self):
        """Вычисляет позицию и показывает окно"""
        screen = QtWidgets.QApplication.primaryScreen()
        if not screen:
            screen = self.screen()  
            
        screen_geom = screen.availableGeometry()

        # Обновляем max_height при смене экрана
        self.max_height = screen_geom.height()

        margin = 10  
        new_x = screen_geom.right() - self.width() - margin
        
        # Расчет Y теперь использует self.height() (которое динамическое)
        new_y = screen_geom.bottom() - self.height() - margin
        
        self.move(new_x, new_y)
        self.show()
        self.activateWindow()

    def on_tray_clicked(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:  
            if self.isVisible():
                self.hide()
                if self.archive_window:
                    self.archive_window.hide()
            else:
                self.show_and_position()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if self.archive_window:
            self.archive_window.hide()

# --- Запуск приложения ---
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    
    app.setQuitOnLastWindowClosed(False)  
    
    main_window = SimpleTodo()
    
    sys.exit(app.exec())