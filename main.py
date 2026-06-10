import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QDate
import pymysql


# ============================================================
# ДЭ 09.02.07 — В3 ПУ. Магазин стройматериалов.
# Модули 1-4: БД, авторизация+карточки, поиск/CRUD товаров, заказы.
# ============================================================

ORANGE = "#F4A460"   # скидка > 12% (В3 — другой цвет!)
BLUE = "#ADD8E6"     # нет на складе
NO_PHOTO = "images/picture.png"


def get_con():
    return pymysql.connect(
        host="localhost", user="root", password="Snejok2015",
        database="materials_db", autocommit=True)


# ============================================================
# ОКНО ВХОДА
# ============================================================
class AuthWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setMinimumSize(400, 300)

        lay = QVBoxLayout()
        self.login = QLineEdit()
        self.login.setPlaceholderText("Логин")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Пароль")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        btn = QPushButton("Войти")
        btn.clicked.connect(self.auth)
        btn_guest = QPushButton("Войти как гость")
        btn_guest.clicked.connect(self.enter_guest)

        lay.addWidget(QLabel("Вход в систему"))
        lay.addWidget(self.login)
        lay.addWidget(self.password)
        lay.addWidget(btn)
        lay.addWidget(btn_guest)
        self.setLayout(lay)

    def auth(self):
        con = get_con()
        cur = con.cursor()
        cur.execute(
            """SELECT u.last_name, u.name, u.middle_name, r.role_name
               FROM users u JOIN roles r ON u.role = r.id
               WHERE u.login=%s AND u.password=%s""",
            (self.login.text(), self.password.text()))
        user = cur.fetchone()
        if user:
            last_name, name, middle_name, role = user
            self.open_window(role, name, middle_name, last_name)
        else:
            QMessageBox.critical(self, "Ошибка", "Неверный логин или пароль")

    def enter_guest(self):
        self.open_window("guest", "", "", "Гость")

    def open_window(self, role, name, middle_name, last_name):
        self.win = MainWindow(self, name, middle_name, last_name, role)
        self.win.show()
        self.hide()


# ============================================================
# ГЛАВНОЕ ОКНО (каталог товаров)
# ============================================================
class MainWindow(QWidget):
    def __init__(self, auth_window, name, middle_name, last_name, role):
        super().__init__()
        self.auth_window = auth_window
        self.role = role
        self.name = name
        self.middle_name = middle_name
        self.last_name = last_name
        self.form_open = False  # запрет двух окон редактирования

        self.setWindowTitle("Каталог стройматериалов")
        self.setMinimumSize(800, 700)
        main_layout = QVBoxLayout()

        # ---- шапка: выход + ФИО ----
        top = QHBoxLayout()
        back_btn = QPushButton("Выйти")
        back_btn.clicked.connect(self.back)
        top.addWidget(back_btn)
        top.addStretch()
        top.addWidget(QLabel(f"{last_name} {name} {middle_name}"))
        main_layout.addLayout(top)

        # ---- поиск/сортировка/фильтр (менеджер и админ) ----
        if self.role in ("manager", "admin"):
            self.search = QLineEdit()
            self.search.setPlaceholderText("Поиск...")
            self.search.textChanged.connect(self.load_products)
            main_layout.addWidget(self.search)

            # сортировка по 3 полям × 2 направления (В3!)
            self.sort = QComboBox()
            self.sort.addItems([
                "Без сортировки",
                "Количество ↑", "Количество ↓",
                "Цена ↑",       "Цена ↓",
                "Скидка ↑",     "Скидка ↓",
            ])
            self.sort.currentIndexChanged.connect(self.load_products)
            main_layout.addWidget(self.sort)

            # фильтр ПО ПРОИЗВОДИТЕЛЮ (В3, а не по поставщику!)
            self.manuf_filter = QComboBox()
            self.manuf_filter.addItem("Все производители", None)
            con = get_con(); cur = con.cursor()
            cur.execute("SELECT manufacturer_name FROM manufacturers")
            for m in cur.fetchall():
                self.manuf_filter.addItem(m[0], m[0])
            self.manuf_filter.currentIndexChanged.connect(self.load_products)
            main_layout.addWidget(self.manuf_filter)

        # ---- кнопки админа/менеджера ----
        btns = QHBoxLayout()
        if self.role == "admin":
            add_btn = QPushButton("Добавить товар")
            add_btn.clicked.connect(self.add_product)
            btns.addWidget(add_btn)
        if self.role in ("manager", "admin"):
            orders_btn = QPushButton("Заказы")
            orders_btn.clicked.connect(self.open_orders)
            btns.addWidget(orders_btn)
        if btns.count():
            main_layout.addLayout(btns)

        # ---- область карточек ----
        self.products_scroll = QScrollArea()
        self.products_scroll.setWidgetResizable(True)
        main_layout.addWidget(self.products_scroll)

        self.setLayout(main_layout)
        self.load_products()

    def get_products(self):
        con = get_con()
        cur = con.cursor()
        cur.execute("""SELECT p.id, p.product_name, p.product_price, p.current_discount,
                        p.unit, m.manufacturer_name, s.supplier_name, pc.category_name,
                        p.quantity, p.product_description, p.image,
                        p.product_category, p.product_manufacturer, p.product_supplier
                        FROM products p
                        JOIN manufacturers m ON p.product_manufacturer = m.id
                        JOIN suppliers s ON p.product_supplier = s.id
                        JOIN product_categories pc ON p.product_category = pc.id""")
        return list(cur.fetchall())  # ← ИСПРАВЛЕНО: преобразуем кортеж в список

    def load_products(self):
        rows = self.get_products()  # теперь это список

        if self.role in ("manager", "admin"):
            # поиск по всем текстовым полям
            text = self.search.text().strip().lower()
            if text:
                new = []
                for r in rows:
                    # r[1]=name, r[5]=manuf, r[6]=supplier, r[7]=category, r[9]=desc
                    line = f"{r[1]} {r[5]} {r[6]} {r[7]} {r[9]}".lower()
                    if text in line:
                        new.append(r)
                rows = new

            # фильтр по производителю (r[5] = manufacturer_name)
            mf = self.manuf_filter.currentData()
            if mf:
                rows = [r for r in rows if r[5] == mf]

            # сортировка — 6 вариантов
            idx = self.sort.currentIndex()
            if idx == 1:  rows.sort(key=lambda r: r[8])                    # кол-во ↑
            elif idx == 2: rows.sort(key=lambda r: r[8], reverse=True)     # кол-во ↓
            elif idx == 3: rows.sort(key=lambda r: r[2])                    # цена ↑
            elif idx == 4: rows.sort(key=lambda r: r[2], reverse=True)     # цена ↓
            elif idx == 5: rows.sort(key=lambda r: r[3])                    # скидка ↑
            elif idx == 6: rows.sort(key=lambda r: r[3], reverse=True)     # скидка ↓

        # рисуем карточки
        container = QFrame()
        container_layout = QVBoxLayout()
        for r in rows:
            container_layout.addWidget(self.make_card(r))
        container.setLayout(container_layout)
        self.products_scroll.setWidget(container)

    def make_card(self, r):
        (pid, product_name, product_price, current_discount, unit,
         manufacturer_name, supplier_name, category_name, quantity,
         product_description, image_path,
         category_id, manuf_id, supplier_id) = r

        card = QFrame()
        card_layout = QHBoxLayout()
        card.setStyleSheet("background-color: white; color: black")

        # фото слева
        if image_path is None:
            image_path = NO_PHOTO
        photo_label = QLabel()
        photo_label.setFixedSize(200, 200)
        photo_label.setStyleSheet("border: 3px solid black")
        photo_label.setPixmap(QPixmap(image_path).scaled(200, 200))
        card_layout.addWidget(photo_label)

        # описание в центре
        info_layout = QVBoxLayout()
        name_label = QLabel(f"{category_name} | {product_name}")
        name_label.setStyleSheet("font-size: 18px; font-weight:bold")
        info_layout.addWidget(name_label)
        desc = QLabel(f"Описание товара: {product_description}")
        desc.setWordWrap(True)
        info_layout.addWidget(desc)
        info_layout.addWidget(QLabel(f"Производитель: {manufacturer_name}"))
        info_layout.addWidget(QLabel(f"Поставщик: {supplier_name}"))

        # цена с зачёркиванием при скидке
        if current_discount != 0:
            price_layout = QHBoxLayout()
            old = QLabel(f"{product_price}р")
            old.setStyleSheet("text-decoration: line-through; color: red")
            new_price = product_price - (product_price * current_discount / 100)
            price_layout.addWidget(QLabel("Цена:"))
            price_layout.addWidget(old)
            price_layout.addWidget(QLabel(f"{new_price:.2f}р"))
            price_layout.addStretch()
            info_layout.addLayout(price_layout)
        else:
            info_layout.addWidget(QLabel(f"Цена: {product_price}р"))

        info_layout.addWidget(QLabel(f"Единица измерения: {unit}"))
        info_layout.addWidget(QLabel(f"Количество на складе: {quantity}"))

        if self.role == "admin":
            card.mousePressEvent = lambda e, prod=r: self.edit_product(prod)
        card_layout.addLayout(info_layout)

        # скидка справа
        discount_label = QLabel(f"Действующая скидка {current_discount}%")
        discount_label.setFixedSize(180, 200)
        discount_label.setStyleSheet("border: 3px solid black")
        card_layout.addWidget(discount_label)

        # подсветка (В3: > 12% → оранжевый!)
        if quantity == 0:
            card.setStyleSheet(f"background-color: {BLUE}; color: black")
        elif current_discount > 12:
            card.setStyleSheet(f"background-color: {ORANGE}; color: black")

        card.setLayout(card_layout)
        return card

    # ============================================================
    # ДОБАВЛЕНИЕ / РЕДАКТИРОВАНИЕ / УДАЛЕНИЕ ТОВАРОВ
    # ============================================================
    def add_product(self):
        if self.form_open:
            return
        self.product_form(None)

    def edit_product(self, prod):
        if self.form_open:
            return
        self.product_form(prod)

    def product_form(self, prod):
        self.form_open = True
        dlg = QDialog(self)
        dlg.setWindowTitle("Редактирование товара" if prod else "Добавление товара")
        f = QFormLayout(dlg)

        # ID показываем только при редактировании (readonly)
        if prod:
            id_label = QLabel(str(prod[0]))
            f.addRow("ID:", id_label)

        name = QLineEdit(prod[1] if prod else "")
        f.addRow("Наименование:", name)

        # категория — выпадающий список
        cat = QComboBox()
        con = get_con(); cur = con.cursor()
        cur.execute("SELECT id, category_name FROM product_categories")
        for c in cur.fetchall():
            cat.addItem(c[1], c[0])
        f.addRow("Категория:", cat)

        # производитель — выпадающий список
        manuf = QComboBox()
        cur.execute("SELECT id, manufacturer_name FROM manufacturers")
        for m in cur.fetchall():
            manuf.addItem(m[1], m[0])
        f.addRow("Производитель:", manuf)

        # поставщик
        sup = QComboBox()
        cur.execute("SELECT id, supplier_name FROM suppliers")
        for s in cur.fetchall():
            sup.addItem(s[1], s[0])
        f.addRow("Поставщик:", sup)

        desc = QLineEdit(prod[9] if prod else "")
        f.addRow("Описание:", desc)
        price = QDoubleSpinBox()
        price.setMaximum(1000000); price.setDecimals(2); price.setMinimum(0)
        f.addRow("Цена:", price)
        unit = QLineEdit(prod[4] if prod else "шт")
        f.addRow("Ед. изм.:", unit)
        qty = QSpinBox(); qty.setMaximum(1000000); qty.setMinimum(0)
        f.addRow("Количество:", qty)
        disc = QSpinBox(); disc.setMaximum(100); disc.setMinimum(0)
        f.addRow("Скидка %:", disc)

        if prod:
            price.setValue(float(prod[2]))
            disc.setValue(prod[3])
            qty.setValue(prod[8])
            cat.setCurrentIndex(cat.findData(prod[11]))
            manuf.setCurrentIndex(manuf.findData(prod[12]))
            sup.setCurrentIndex(sup.findData(prod[13]))

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(dlg.accept)
        f.addRow(btn_save)
        if prod:
            btn_del = QPushButton("Удалить")
            btn_del.clicked.connect(lambda: self.delete_product(prod, dlg))
            f.addRow(btn_del)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            if not name.text().strip():
                QMessageBox.warning(self, "Ошибка", "Введите наименование")
                self.form_open = False
                return
            con = get_con(); cur = con.cursor()
            if prod:
                cur.execute(
                    "UPDATE products SET product_name=%s, product_description=%s, "
                    "product_category=%s, product_manufacturer=%s, product_supplier=%s, "
                    "product_price=%s, current_discount=%s, unit=%s, quantity=%s "
                    "WHERE id=%s",
                    (name.text(), desc.text(), cat.currentData(), manuf.currentData(),
                     sup.currentData(), price.value(), disc.value(), unit.text(),
                     qty.value(), prod[0]))
            else:
                cur.execute(
                    "INSERT INTO products(product_name, product_description, "
                    "product_category, product_manufacturer, product_supplier, "
                    "product_price, current_discount, unit, quantity) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (name.text(), desc.text(), cat.currentData(), manuf.currentData(),
                     sup.currentData(), price.value(), disc.value(), unit.text(),
                     qty.value()))
            self.load_products()
        self.form_open = False

    def delete_product(self, prod, dlg):
        con = get_con(); cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM order_items WHERE product_id=%s", (prod[0],))
        if cur.fetchone()[0] > 0:
            QMessageBox.warning(self, "Нельзя", "Товар есть в заказе, удалить нельзя")
            return
        cur.execute("DELETE FROM products WHERE id=%s", (prod[0],))
        dlg.reject()
        self.form_open = False
        self.load_products()

    # ============================================================
    # МОДУЛЬ 4 — ЗАКАЗЫ
    # ============================================================
    def open_orders(self):
        self.orders_win = OrdersWindow(self)
        self.orders_win.show()

    def back(self):
        self.close()
        self.auth_window.show()


# ============================================================
# ОКНО ЗАКАЗОВ (Модуль 4)
# ============================================================
class OrdersWindow(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.role = parent_window.role
        self.form_open = False

        self.setWindowTitle("Заказы")
        self.setMinimumSize(700, 600)
        main_layout = QVBoxLayout()

        # шапка с кнопкой назад
        top = QHBoxLayout()
        back_btn = QPushButton("Назад")
        back_btn.clicked.connect(self.close)
        top.addWidget(back_btn)
        top.addStretch()
        main_layout.addLayout(top)

        # кнопка добавить — только админ
        if self.role == "admin":
            add_btn = QPushButton("Добавить заказ")
            add_btn.clicked.connect(self.add_order)
            main_layout.addWidget(add_btn)

        # область карточек заказов
        self.orders_scroll = QScrollArea()
        self.orders_scroll.setWidgetResizable(True)
        main_layout.addWidget(self.orders_scroll)

        self.setLayout(main_layout)
        self.load_orders()

    def get_orders(self):
        con = get_con(); cur = con.cursor()
        cur.execute("""SELECT o.id, o.order_article, os.status_name,
                        o.pickup_address, o.order_date, o.delivery_date, o.status
                        FROM orders o
                        JOIN order_statuses os ON o.status = os.id""")
        return list(cur.fetchall())  # ← ИСПРАВЛЕНО: преобразуем кортеж в список

    def load_orders(self):
        orders = self.get_orders()  # теперь это список
        container = QFrame()
        container_layout = QVBoxLayout()
        for o in orders:
            container_layout.addWidget(self.make_order_card(o))
        container.setLayout(container_layout)
        self.orders_scroll.setWidget(container)

    def make_order_card(self, o):
        """Карточка заказа: слева инфо, справа дата доставки (по макету ТЗ)."""
        order_id, article, status_name, address, order_date, delivery_date, _ = o

        card = QFrame()
        card.setStyleSheet("background-color: white; color: black; border: 1px solid black")
        card.setFixedHeight(140)
        row = QHBoxLayout(card)

        # левая часть — основная инфа
        info = QVBoxLayout()
        article_label = QLabel(f"Артикул заказа: {article}")
        article_label.setStyleSheet("font-weight: bold; font-size: 16px")
        info.addWidget(article_label)
        info.addWidget(QLabel(f"Статус заказа: {status_name}"))
        info.addWidget(QLabel(f"Адрес пункта выдачи: {address}"))
        info.addWidget(QLabel(f"Дата заказа: {order_date}"))
        row.addLayout(info, stretch=1)

        # правая часть — дата доставки
        delivery = QLabel(f"Дата доставки:\n{delivery_date}")
        delivery.setStyleSheet("border-left: 1px solid black; padding: 10px")
        delivery.setFixedWidth(180)
        row.addWidget(delivery)

        # клик → редактирование (админ)
        if self.role == "admin":
            card.mousePressEvent = lambda e, ord=o: self.edit_order(ord)
        return card

    def add_order(self):
        if self.form_open:
            return
        self.order_form(None)

    def edit_order(self, ord):
        if self.form_open:
            return
        self.order_form(ord)

    def order_form(self, ord):
        self.form_open = True
        dlg = QDialog(self)
        dlg.setWindowTitle("Редактирование заказа" if ord else "Добавление заказа")
        f = QFormLayout(dlg)

        article = QLineEdit(ord[1] if ord else "")
        f.addRow("Артикул:", article)

        # статус — выпадающий список
        status = QComboBox()
        con = get_con(); cur = con.cursor()
        cur.execute("SELECT id, status_name FROM order_statuses")
        for s in cur.fetchall():
            status.addItem(s[1], s[0])
        f.addRow("Статус:", status)

        address = QLineEdit(ord[3] if ord else "")
        f.addRow("Адрес пункта выдачи:", address)

        order_date = QDateEdit()
        order_date.setCalendarPopup(True)
        order_date.setDate(QDate.currentDate())
        f.addRow("Дата заказа:", order_date)

        delivery_date = QDateEdit()
        delivery_date.setCalendarPopup(True)
        delivery_date.setDate(QDate.currentDate().addDays(5))
        f.addRow("Дата доставки:", delivery_date)

        if ord:
            status.setCurrentIndex(status.findData(ord[6]))
            if ord[4]:
                order_date.setDate(QDate(ord[4].year, ord[4].month, ord[4].day))
            if ord[5]:
                delivery_date.setDate(QDate(ord[5].year, ord[5].month, ord[5].day))

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(dlg.accept)
        f.addRow(btn_save)
        if ord:
            btn_del = QPushButton("Удалить")
            btn_del.clicked.connect(lambda: self.delete_order(ord, dlg))
            f.addRow(btn_del)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            if not article.text().strip():
                QMessageBox.warning(self, "Ошибка", "Введите артикул")
                self.form_open = False
                return
            con = get_con(); cur = con.cursor()
            od = order_date.date().toString("yyyy-MM-dd")
            dd = delivery_date.date().toString("yyyy-MM-dd")
            if ord:
                cur.execute(
                    "UPDATE orders SET order_article=%s, status=%s, pickup_address=%s, "
                    "order_date=%s, delivery_date=%s WHERE id=%s",
                    (article.text(), status.currentData(), address.text(), od, dd, ord[0]))
            else:
                cur.execute(
                    "INSERT INTO orders(order_article, status, pickup_address, "
                    "order_date, delivery_date) VALUES (%s,%s,%s,%s,%s)",
                    (article.text(), status.currentData(), address.text(), od, dd))
            self.load_orders()
        self.form_open = False

    def delete_order(self, ord, dlg):
        con = get_con(); cur = con.cursor()
        cur.execute("DELETE FROM orders WHERE id=%s", (ord[0],))
        dlg.reject()
        self.form_open = False
        self.load_orders()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = AuthWindow()
    w.show()
    app.exec()
