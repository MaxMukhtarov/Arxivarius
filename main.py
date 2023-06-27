import sys
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QMenu, QWidget, QVBoxLayout, QLineEdit, QListWidget, \
    QDialog, QLabel, QStackedWidget, QPushButton, QHBoxLayout, QSizePolicy, QToolButton, QMessageBox, QCompleter, QTextBrowser, QTextEdit
from PyQt5.QtGui import QImage, QPalette, QPainter, QBrush, QPixmap, QClipboard, QGuiApplication
from PyQt5.QtCore import Qt, QEvent, QRect, QMimeData, QStringListModel, QSortFilterProxyModel
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
import time
import sqlite3
import qrcode
from reportlab.pdfgen import canvas
import os
import shutil


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Arxivarius")
        self.setGeometry(100, 100, 800, 600)

        self.stacked_widget = QStackedWidget(self)
        self.setCentralWidget(self.stacked_widget)

        self.main_window = QWidget()
        self.stacked_widget.addWidget(self.main_window)

        self.search_window = SearchWindow()
        self.stacked_widget.addWidget(self.search_window)

        self.edit_window = EditWindow()
        self.stacked_widget.addWidget(self.edit_window)

        self.stacked_widget.setCurrentWidget(self.main_window)

        self.set_background_image()
        self.create_menus()

    def set_background_image(self):

        image = QImage("newbg.png")

        size = self.size()

        image = image.scaled(size)

        brush = QBrush(image)

        palette = self.palette()
        palette.setBrush(QPalette.Background, brush)
        self.setPalette(palette)

    def resizeEvent(self, event):

        self.set_background_image()
        return QMainWindow.resizeEvent(self, event)

    def create_menus(self):
        menubar = self.menuBar()

        bosh_sahifa_menu = menubar.addMenu("Bosh sahifa")
        self.create_action(bosh_sahifa_menu, "Bosh sahifa", self.redirect_to_main_window)

        qidiruv_menu = menubar.addMenu("Qidiruv")
        self.create_action(qidiruv_menu, "Qidirish", self.redirect_to_search_window)

        fayllarni_taxrirlash_menu = menubar.addMenu("Fayllarni taxrirlash")
        self.create_action(fayllarni_taxrirlash_menu, "Fayllarni taxrirlash", self.redirect_to_edit_window)

    def create_action(self, menu, name, slot):
        action = QAction(name, self)

        action.triggered.connect(slot)

        menu.addAction(action)

    def redirect_to_main_window(self):

        self.stacked_widget.setCurrentWidget(self.main_window)

    def redirect_to_search_window(self):

        self.stacked_widget.setCurrentWidget(self.search_window)

    def redirect_to_edit_window(self):

        self.stacked_widget.setCurrentWidget(self.edit_window)


class SearchWindow(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.search_bar = QLineEdit()
        self.search_bar.textChanged.connect(self.search_data)
        layout.addWidget(self.search_bar)

        self.result_list = QListWidget()
        self.result_list.doubleClicked.connect(self.display_complete_data)
        layout.addWidget(self.result_list)

    def search_data(self):

        query = self.search_bar.text().strip().lower()
        self.result_list.clear()

        if not query:
            return

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("SELECT nomi FROM files WHERE LOWER(nomi) LIKE '%' || ? || '%'", (query,))

        rows = c.fetchall()

        for row in rows:
            self.result_list.addItem(row[0])

        conn.close()

    def display_complete_data(self, index):

        selected_item_name = self.result_list.item(index.row()).text()

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("SELECT * FROM files WHERE nomi = ?", (selected_item_name,))
        row = c.fetchone()

        conn.close()

        if row:
            data = {
                'nomi': row[1],
                'code': row[2],
                'status':row[3],
            }

            self.display_dialog = DisplayDialog(data)
            self.display_dialog.exec_()


class AddFileModule(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        nomi_label = QLabel("Nomi:")
        self.nomi_input = QLineEdit()
        layout.addWidget(nomi_label)
        layout.addWidget(self.nomi_input)

        code_layout = QHBoxLayout()
        layout.addLayout(code_layout)

        code_labels = []
        self.code_inputs = []
        for i in range(6):
            input_field = QLineEdit()
            self.code_inputs.append(input_field)
            code_layout.addWidget(input_field)

            if i != 5:
                code_layout.addWidget(QLabel(":"))

            if i == 5:
                input_field.setMaxLength(4)
                input_field.setFixedWidth(100)
                input_field.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            else:
                input_field.setMaxLength(2)
                input_field.setFixedWidth(50)
                input_field.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

            input_field.textChanged.connect(lambda text, field=input_field: self.handle_code_input(text, field))

        add_button = QPushButton("Qo`shish")
        add_button.clicked.connect(self.add_file)
        layout.addWidget(add_button)

        self.setStyleSheet("""
            QLabel {
                font-weight: bold;
                margin-bottom: 5px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
            }
            QPushButton {
                padding: 5px 10px;
                background-color: #4CAF50;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.create_files_table()

    def handle_code_input(self, text, field):
        if len(text) == field.maxLength():
            next_index = self.code_inputs.index(field) + 1
            if next_index < len(self.code_inputs):
                self.code_inputs[next_index].setFocus()

    def create_files_table(self):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nomi TEXT,
                        code TEXT,
                        status INTEGER,
                        olingan_vaqti TEXT
                    )''')
        conn.commit()
        conn.close()

    def add_file(self):
        nomi = self.nomi_input.text().strip()

        code_parts = []
        for input_field in self.code_inputs:
            code_part = input_field.text().strip()
            if not code_part:
                return
            code_parts.append(code_part)

        code = ":".join(code_parts)

        if not nomi or not code:
            return

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('INSERT INTO files (nomi, code, status, olingan_vaqti) VALUES (?, ?, ?, ?)',
                  (nomi, code, 0, ''))

        conn.commit()
        conn.close()

        self.nomi_input.clear()
        for input_field in self.code_inputs:
            input_field.clear()


class EditFileModule(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        search_label = QLabel("Qidirish:")
        self.search_input = QLineEdit()
        layout.addWidget(search_label)
        layout.addWidget(self.search_input)

        edit_button = QPushButton("Taxrirlash")
        edit_button.clicked.connect(self.edit_file)
        layout.addWidget(edit_button)

        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        code_layout = QHBoxLayout()
        layout.addLayout(code_layout)

        self.code_inputs = []
        for i in range(5):
            code_input = QLineEdit()
            code_input.setMaxLength(2)
            code_input.setFixedWidth(40)
            self.code_inputs.append(code_input)
            code_layout.addWidget(code_input)

        last_code_input = QLineEdit()
        last_code_input.setMaxLength(4)
        last_code_input.setFixedWidth(80)
        self.code_inputs.append(last_code_input)
        code_layout.addWidget(last_code_input)

        self.history_input = QTextEdit()
        layout.addWidget(self.history_input)

        save_button = QPushButton("Saqlash")
        save_button.clicked.connect(self.save_file)
        layout.addWidget(save_button)

        # Initialize variables
        self.selected_item = None

        self.setStyleSheet("""
            QLabel {
                font-weight: bold;
                margin-bottom: 5px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
            }
            QPushButton {
                padding: 5px 10px;
                background-color: #4CAF50;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTextEdit {
                padding: 5px;
                border: 1px solid #ccc;
            }
        """)

        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.search_input.textChanged.connect(self.clear_data)

        completer = QCompleter(self)
        self.search_input.setCompleter(completer)

        completer_model = self.createCompleterModel()
        completer.setModel(completer_model)
        completer.setCompletionColumn(0)
        completer.setCaseSensitivity(Qt.CaseInsensitive)

    def createCompleterModel(self):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('SELECT nomi FROM files')
        suggestions = c.fetchall()

        conn.close()

        model = QStringListModel()
        model.setStringList([s[0] for s in suggestions])

        return model

    def edit_file(self):
        query = self.search_input.text().strip()

        if not query:
            return

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('SELECT * FROM files WHERE nomi = ?', (query,))
        item = c.fetchone()

        conn.close()

        if item:
            self.selected_item = item
            self.name_input.setText(item[1])

            code_parts = item[2].split(':')
            for i in range(min(len(code_parts), len(self.code_inputs))):
                self.code_inputs[i].setText(code_parts[i])

            for i in range(len(code_parts), len(self.code_inputs)):
                self.code_inputs[i].clear()

            for code_input in self.code_inputs:
                code_input.setReadOnly(False)
        else:
            self.selected_item = None
            self.name_input.clear()
            for code_input in self.code_inputs:
                code_input.clear()
                code_input.setReadOnly(False)

    def save_file(self):
        if not self.selected_item:
            return

        name = self.name_input.text().strip()
        code_parts = []
        for code_input in self.code_inputs:
            code_part = code_input.text().strip()
            if code_part:
                code_parts.append(code_part)

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute('UPDATE files SET nomi = ?, code = ? WHERE nomi = ?',
                  (name, ':'.join(code_parts), self.selected_item[1]))

        conn.commit()
        conn.close()

        self.selected_item = None
        self.name_input.clear()
        for code_input in self.code_inputs:
            code_input.clear()
            code_input.setReadOnly(True)

    def clear_data(self):
        if not self.search_input.text().strip():
            self.selected_item = None
            self.name_input.clear()
            for code_input in self.code_inputs:
                code_input.clear()
                code_input.setReadOnly(False)
            self.history_input.clear()


class GetFileModule(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)

        self.frame = QtWidgets.QFrame(self)
        self.frame.setFixedSize(200, 200)
        self.frame.setStyleSheet("background-color: black;")

        # Create a horizontal layout to center the frame horizontally
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addStretch(1)  # Add stretch to align the frame to the center horizontally
        hlayout.addWidget(self.frame)
        hlayout.addStretch(1)  # Add stretch to align the frame to the center horizontally

        layout.addLayout(hlayout)

        search_label = QtWidgets.QLabel("Qidirish:")
        self.search_input = QtWidgets.QLineEdit()
        layout.addWidget(search_label)
        layout.addWidget(self.search_input)

        get_button = QtWidgets.QPushButton("Olish")
        get_button.clicked.connect(self.get_file)
        layout.addWidget(get_button)

        qr_button = QtWidgets.QPushButton("QR kod orqali olish")
        qr_button.clicked.connect(self.scan_qr_code)
        layout.addWidget(qr_button)

        self.file_completer = QtWidgets.QCompleter()
        self.file_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.search_input.setCompleter(self.file_completer)

        self.proxy_model = QtCore.QSortFilterProxyModel()
        self.proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.file_completer.setModel(self.proxy_model)

        self.load_file_suggestions()

        self.search_input.textChanged.connect(self.filter_file_suggestions)

    def load_file_suggestions(self):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("SELECT nomi, code FROM files")
        rows = c.fetchall()

        file_suggestions = [row[0] for row in rows] + [row[1] for row in rows]

        self.proxy_model.setSourceModel(QtCore.QStringListModel(file_suggestions))

        conn.close()

    def filter_file_suggestions(self, text):
        self.proxy_model.setFilterFixedString(text)

    def get_file(self):
        query = self.search_input.text().strip()

        if not query:
            return

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("SELECT status, olingan_vaqti FROM files WHERE nomi = ? OR code = ?", (query, query))
        result = c.fetchone()

        if result:
            status = result[0]
            olingan_vaqti = result[1]

            if status == 1:
                QtWidgets.QMessageBox.information(self, "Fayl olingan", "Bu fayl olingan.")
            else:
                acquisition_time = QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.ISODate)
                if olingan_vaqti:
                    olingan_vaqti = olingan_vaqti.split(',')
                    olingan_vaqti.append(acquisition_time)
                    olingan_vaqti = ','.join(olingan_vaqti)
                else:
                    olingan_vaqti = acquisition_time

                c.execute("UPDATE files SET status = 1, olingan_vaqti = ? WHERE nomi = ? OR code = ?",
                          (olingan_vaqti, query, query))
                conn.commit()

                QtWidgets.QMessageBox.information(self, "Fayl olindi", "OLINDI.")

        conn.close()

        self.search_input.clear()

    def scan_qr_code(self):
        pass



class PDFModule(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)

        file_label = QtWidgets.QLabel("Fayllarni tanlang:")
        layout.addWidget(file_label)

        self.file_list = QtWidgets.QListWidget()
        layout.addWidget(self.file_list)

        browse_button = QtWidgets.QPushButton("Qidirish")
        browse_button.clicked.connect(self.browse_files)
        layout.addWidget(browse_button)

        copy_button = QtWidgets.QPushButton("Nusxa olish")
        copy_button.clicked.connect(self.copy_files)
        layout.addWidget(copy_button)

    def browse_files(self):
        file_dialog = QtWidgets.QFileDialog()
        file_dialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("PDF files (*.pdf)")
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            self.file_list.clear()
            self.file_list.addItems(selected_files)

    def copy_files(self):
        destination_folder = "pdflar"
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)

        for index in range(self.file_list.count()):
            source_file = self.file_list.item(index).text()
            destination_file = os.path.join(destination_folder, os.path.basename(source_file))

            if os.path.exists(destination_file):
                QtWidgets.QMessageBox.warning(self, "Fayl allaqachon mavjud",
                                              "Fayl allaqachon mavjud: {}".format(destination_file))
            else:
                try:
                    shutil.copy(source_file, destination_file)
                except IOError as e:
                    print("Ushbu faylni ko`chirishda muvaffaqiyatsizlik:", e)

                QtWidgets.QMessageBox.information(self, "Nusxa olindi", "Fayllar muvaffaqiyatli nusxa olindi.")

        self.file_list.clear()


class ReturnFileModule(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        search_label = QLabel("Qidirish:")
        self.search_input = QLineEdit()
        layout.addWidget(search_label)
        layout.addWidget(self.search_input)

        completer = QCompleter()
        self.search_input.setCompleter(completer)

        get_button = QPushButton("Qaytarish")
        get_button.clicked.connect(self.return_file)
        layout.addWidget(get_button)

        self.setStyleSheet("""
            QLabel {
                font-weight: bold;
                margin-bottom: 5px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
            }
            QPushButton {
                padding: 5px 10px;
                background-color: #4CAF50;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.load_suggestions()

    def load_suggestions(self):

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("SELECT nomi FROM files")
        results = c.fetchall()

        file_names = [result[0] for result in results]

        completer = self.search_input.completer()
        model = QtGui.QStandardItemModel()
        completer.setModel(model)

        for file_name in file_names:
            item = QtGui.QStandardItem(file_name)
            model.appendRow(item)

        conn.close()

    def return_file(self):
        query = self.search_input.text().strip()

        if not query:
            return

        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("SELECT status FROM files WHERE (nomi = ? OR code = ?) AND status = 1", (query, query))
        result = c.fetchone()

        if result:
            c.execute("UPDATE files SET status = 0 WHERE nomi = ? OR code = ?", (query, query))
            conn.commit()

            QMessageBox.information(self, "Fayl qaytarildi", "Fayl muvaffaqiyatli qaytarildi.")
        else:
            QMessageBox.information(self, "Fayl olinmagan", "Bu fayl olinmagan yoki avval qaytarilgan.")

        conn.close()

        self.search_input.clear()


class QRCodeModule(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        code_layout = QHBoxLayout()
        layout.addLayout(code_layout)

        self.code_inputs = []
        for i in range(5):
            code_input = QLineEdit()
            code_input.setMaxLength(2)
            code_input.setFixedWidth(40)
            self.code_inputs.append(code_input)
            code_layout.addWidget(code_input)

            if i < 5:
                colon_label = QLabel(":")
                code_layout.addWidget(colon_label)

        last_code_input = QLineEdit()
        last_code_input.setMaxLength(4)
        last_code_input.setFixedWidth(80)
        self.code_inputs.append(last_code_input)
        code_layout.addWidget(last_code_input)

        create_button = QPushButton("QR kod yaratish")
        create_button.clicked.connect(self.create_qr_code)
        layout.addWidget(create_button)

        self.qr_code_label = QLabel()
        self.qr_code_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.qr_code_label)

        copy_button = QPushButton("QR kodni ko`chirish")
        copy_button.clicked.connect(self.copy_qr_code)
        layout.addWidget(copy_button)

        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

    def create_qr_code(self):
        name = self.name_input.text().strip()
        code_parts = []
        for code_input in self.code_inputs:
            code_part = code_input.text().strip()
            if code_part:
                code_parts.append(code_part)

        if not name or len(code_parts) != 6:
            QMessageBox.warning(self, "Invalid Data", "Please enter a valid name and code.")
            return

        file_name = f"{name}_{':'.join(code_parts)}.png"
        qr_code = qrcode.make(file_name)
        qr_code_path = f"qrcode/{file_name}"
        qr_code.save(qr_code_path)

        self.display_qr_code(qr_code_path)

    def display_qr_code(self, path):
        pixmap = QPixmap(path)
        scaled_pixmap = pixmap.scaledToWidth(200)
        self.qr_code_label.setPixmap(scaled_pixmap)

    def copy_qr_code(self):
        clipboard = QApplication.clipboard()
        pixmap = self.qr_code_label.pixmap()
        clipboard.setPixmap(pixmap)
        QMessageBox.information(self, "QR kod ko`chirib olindi", "QR kod klipbordga ko`chirib olindi")


class EditWindow(QWidget):
    def __init__(self):
        super().__init__()

        layout = QtWidgets.QVBoxLayout(self)

        self.toggle_button = QtWidgets.QToolButton(self)
        self.toggle_button.setIcon(QtGui.QIcon("menu_icon.png"))
        self.toggle_button.setIconSize(QtCore.QSize(24, 24))
        self.toggle_button.setFixedSize(40, 40)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.clicked.connect(self.toggle_sidebar)
        layout.addWidget(self.toggle_button)

        self.sidebar_container = QWidget(self)
        self.sidebar_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.sidebar_container.setStyleSheet("background-color: #F0F0F0;")

        self.sidebar_layout = QtWidgets.QVBoxLayout(self.sidebar_container)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)

        self.sidebar = Sidebar(self.sidebar_container)
        self.sidebar_layout.addWidget(self.sidebar)

        self.stacked_widget = QtWidgets.QStackedWidget(self)

        layout.addWidget(self.sidebar_container)
        layout.addWidget(self.stacked_widget)

        self.add_file_module = AddFileModule()
        self.stacked_widget.addWidget(self.add_file_module)

        self.pdf_module = PDFModule()
        self.stacked_widget.addWidget(self.pdf_module)

        self.qr_code_module = QRCodeModule()
        self.stacked_widget.addWidget(self.qr_code_module)

        self.get_file_module = GetFileModule()
        self.stacked_widget.addWidget(self.get_file_module)

        self.return_file_module = ReturnFileModule()
        self.stacked_widget.addWidget(self.return_file_module)

        self.edit_file_module = EditFileModule()
        self.stacked_widget.addWidget(self.edit_file_module)

        self.stacked_widget.setCurrentWidget(self.add_file_module)
        self.sidebar.add_file_button.clicked.connect(
            lambda: self.stacked_widget.setCurrentWidget(self.add_file_module)
        )
        self.sidebar.pdf_button.clicked.connect(
            lambda: self.stacked_widget.setCurrentWidget(self.pdf_module)
        )
        self.sidebar.get_file_button.clicked.connect(
            lambda: self.stacked_widget.setCurrentWidget(self.get_file_module)
        )
        self.sidebar.return_file_button.clicked.connect(
            lambda: self.stacked_widget.setCurrentWidget(self.return_file_module)
        )
        self.sidebar.edit_file_button.clicked.connect(
            lambda: self.stacked_widget.setCurrentWidget(self.edit_file_module)
        )
        self.sidebar.qr_code_button.clicked.connect(
            lambda: self.stacked_widget.setCurrentWidget(self.qr_code_module)
        )

        self.sidebar_visible = True

    def toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        self.sidebar_container.setVisible(self.sidebar_visible)
        self.update_layout()

    def update_layout(self):
        if self.sidebar_visible:
            self.toggle_button.setStyleSheet("background-color: #F0F0F0;")
            self.stacked_widget.setStyleSheet("background-color: #FFFFFF;")
        else:
            self.toggle_button.setStyleSheet("background-color: transparent;")
            self.stacked_widget.setStyleSheet("background-color: #F0F0F0;")

        self.layout().update()


class Sidebar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.add_file_button = QPushButton("Faylni qo`shish")
        layout.addWidget(self.add_file_button)

        self.pdf_button = QPushButton("PDF")
        layout.addWidget(self.pdf_button)

        self.get_file_button = QPushButton("Faylni olish")
        layout.addWidget(self.get_file_button)

        self.return_file_button = QPushButton("Faylni qaytarish")
        layout.addWidget(self.return_file_button)

        self.edit_file_button = QPushButton("Faylni taxrirlash")
        layout.addWidget(self.edit_file_button)

        self.qr_code_button = QPushButton("QR olish")
        layout.addWidget(self.qr_code_button)


        self.setStyleSheet("""
            QPushButton {
                padding: 10px;
                background-color: #4CAF50;
                color: white;
                border: none;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)


class DisplayDialog(QDialog):
    def __init__(self, item):
        super().__init__()

        self.item = item

        layout = QVBoxLayout()
        self.setLayout(layout)

        name_label = QLabel(f"Name: {item['nomi']}")
        layout.addWidget(name_label)

        code_label = QLabel(f"Code: {item['code']}")
        layout.addWidget(code_label)

        status_label = QLabel(f"Status: {item['status']}")
        layout.addWidget(status_label)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(item['code'])
        qr.add_data(item['nomi'])
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image.save('qr_code.png')
        qr_label = QLabel()
        qr_label.setPixmap(QPixmap('qr_code.png'))
        layout.addWidget(qr_label)

        pdf_button = QPushButton("PDF olish")
        pdf_button.clicked.connect(self.generate_pdf)
        layout.addWidget(pdf_button)

        # Add Browse History button
        browse_button = QPushButton("Tarix")
        browse_button.clicked.connect(self.browse_history)
        layout.addWidget(browse_button)

        self.history_widget = QTextEdit()
        self.history_widget.setReadOnly(True)

    def generate_pdf(self):
        pdf_file = "item_details.pdf"
        c = canvas.Canvas(pdf_file)

        c.setFont("Helvetica", 12)
        c.drawString(100, 700, f"Name: {self.item['nomi']}")
        c.drawString(100, 660, f"Code: {self.item['code']}")
        c.drawImage('qr_code.png', 100, 600, 200, 200)

        c.save()

        QMessageBox.information(self, "PDF olish", "PDF muvaffaqiyatli olingan!")

    def browse_history(self):
        conn = sqlite3.connect('database.db')
        c = conn.cursor()

        c.execute("SELECT olingan_vaqti FROM files WHERE nomi = ? OR code = ?", (self.item['nomi'], self.item['code']))
        result = c.fetchone()
        if result:
            history = result[0]

            if history == "[]":
                self.history_widget.clear()
                message_label = QLabel("Hali biror marta olinmadi")
                message_label.setAlignment(Qt.AlignCenter)
                message_label.setStyleSheet("color: grey; font-style: italic;")
                self.history_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                self.history_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                self.history_widget.setReadOnly(True)
                self.history_widget.setAlignment(Qt.AlignCenter)  # Center the message label
                self.history_widget.setTextInteractionFlags(Qt.NoTextInteraction)  # Disable text interaction
                self.history_widget.setPlainText("")  # Clear any existing text
                self.history_widget.insertPlainText(message_label.text())  # Insert the message label text
            else:
                history = history.split(',')
                history_text = '\n'.join(history)
                self.history_widget.setPlainText(history_text)
                self.history_widget.setStyleSheet("")
                self.history_widget.setReadOnly(True)

            self.history_widget.setWindowTitle("Olingan vaqti")
            self.history_widget.show()
        else:
            QMessageBox.information(self, "Topilmadi", "Hech qanday ma'lumot topilmadi")

        conn.close()

        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())