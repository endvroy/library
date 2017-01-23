from kivy.config import Config
Config.set('input', 'mouse', 'mouse,disable_multitouch')
Config.set('kivy', 'desktop', 1)
Config.set('graphics', 'window_state', 'maximized')
from kivy.app import App
from kivy.uix.togglebutton import ToggleButton
from kivy.utils import get_color_from_hex as hex_color
from kivy.uix.boxlayout import BoxLayout
from kivy.factory import Factory
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView

from model import *
from datetime import date


class RadioButton(ToggleButton):
    def _do_press(self):
        if self.state == 'normal':
            super()._do_press()


# class OrderByList(BoxLayout):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         self.available = ['title',
#                           'type',
#                           'publisher',
#                           'author',
#                           'year',
#                           'price']
#         self.options = []
#
#     # def add_option(self):
#     #     if


class BookTable(BoxLayout):
    def refresh(self, books):
        self.clear_widgets()
        self.add_widget(Factory.TableHeader())
        book_list = BookList()
        self.add_widget(book_list)
        self.book_list = book_list

        self.book_list.refresh(books)


class BookList(ScrollView):
    def refresh(self, books):
        self.clear_widgets()
        data_grid = Factory.DataGrid()
        self.add_widget(data_grid)
        self.data_grid = data_grid

        self.data_grid.books = books
        self.data_grid.refresh()


class DataGrid(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.books = []
        self.size_hint_y = None
        self.cols = 9

    def render_book(self, book):
        attrs = ['id',
                 'type',
                 'title',
                 'publisher',
                 'year',
                 'author',
                 'price',
                 'total',
                 'stock'
                 ]

        for attr in attrs:
            content = getattr(book, attr)
            if content is None:
                self.add_widget(Factory.RobotoLabel(text='null', italic=True))
            else:
                self.add_widget(Factory.RobotoLabel(text=str(content)))

    def refresh(self):
        for book in self.books:
            self.render_book(book)
        self.height = 50 * len(self.books)


class LibraryRoot(BoxLayout):
    def build_params(self, attrs):
        params = {}
        for x in attrs:
            input = getattr(self.current_page, x + '_input')
            if input.text:
                params[x] = input.text
        return params

    def do_search_books(self):
        attrs = ['title',
                 'type',
                 'publisher',
                 'author',
                 'start_year',
                 'end_year',
                 'start_price',
                 'end_price',
                 'order_by'
                 ]
        params = self.build_params(attrs)

        if 'start_year' in params.keys() or 'end_year' in params.keys():
            params['year'] = int(params['start_year']), int(params['end_year'])
            del params['start_year']
            del params['end_year']
        if 'start_price' in params.keys() or 'end_price' in params.keys():
            params['price'] = float(params['start_price']), float(params['end_price'])
            del params['start_price']
            del params['end_price']
        if 'order_by' in params.keys():
            if params['order_by'] == 'default':
                del params['order_by']
            else:
                params['order_by'] = getattr(books.c, params['order_by'])
                if self.current_page.desc_input.active:
                    params['order_by'] = desc(params['order_by'])

        rp = search_books(**params)
        self.current_page.book_table.refresh(rp.fetchall())

    def do_add_book(self):
        attrs = ['id',
                 'type',
                 'title',
                 'publisher',
                 'year',
                 'author',
                 'price',
                 'total'
                 ]
        params = self.build_params(attrs)

        if 'year' in params.keys():
            params['year'] = int(params['year'])
        if 'price' in params.keys():
            params['price'] = float(params['price'])
        if 'total' in params.keys():
            params['year'] = int(params['total'])

        try:
            self.admin.add_book(**params)
        except Exception as exc:
            self.current_page.error.text = str(exc)
            self.current_page.error.color = hex_color('#FF0000')
        else:
            self.current_page.error.text = 'successful'
            self.current_page.error.color = hex_color('#00FF00')

    def do_import_books(self):
        try:
            self.admin.import_books(self.current_page.path_input.text)
        except Exception as exc:
            self.current_page.error.text = str(exc)
            self.current_page.error.color = hex_color('#FF0000')
        else:
            self.current_page.error.text = 'successful'
            self.current_page.error.color = hex_color('#00FF00')

    def do_list_borrows(self):
        try:
            borrowed_books = self.admin.list_borrows(self.current_page.card_id_input.text)
            self.current_page.book_table.refresh(borrowed_books)
        except Exception as exc:
            self.current_page.error.text = str(exc)
            self.current_page.error.color = hex_color('#FF0000')

    def do_borrow_book(self):
        try:
            attrs = ['year', 'month', 'day']
            params = self.build_params(attrs)
            for x in params.keys():
                params[x] = int(params[x])
            return_date = date(**params)
            self.admin.borrow_book(self.current_page.card_id_input.text,
                                   self.current_page.book_id_input.text,
                                   return_date)
        except ForbiddenOperationError as exc:
            error_text = str(exc)
            error_text += '\nnearest return date: '
            error_text += self.admin.find_nearest_return(
                self.current_page.book_id_input.text).strftime('%Y/%m/%d')
            self.current_page.error.text = error_text
            self.current_page.error.color = hex_color('#FF0000')
        except Exception as exc:
            self.current_page.error.text = str(exc)
            self.current_page.error.color = hex_color('#FF0000')
        else:
            self.current_page.error.text = 'successful'
            self.current_page.error.color = hex_color('#00FF00')

    def do_return_book(self):
        try:
            self.admin.return_book(self.current_page.card_id_input.text,
                                   self.current_page.book_id_input.text)
        except Exception as exc:
            self.current_page.error.text = str(exc)
            self.current_page.error.color = hex_color('#FF0000')
        else:
            self.current_page.error.text = 'successful'
            self.current_page.error.color = hex_color('#00FF00')

    def do_add_card(self):
        attrs = ['id',
                 'dept',
                 'name',
                 'type',
                 ]

        params = self.build_params(attrs)

        try:
            self.admin.add_card(**params)
        except Exception as exc:
            self.current_page.error.text = str(exc)
            self.current_page.error.color = hex_color('#FF0000')
        else:
            self.current_page.error.text = 'successful'
            self.current_page.error.color = hex_color('#00FF00')

    def do_remove_card(self):
        try:
            self.admin.remove_card(self.current_page.id_input.text)
        except Exception as exc:
            self.current_page.error.text = str(exc)
            self.current_page.error.color = hex_color('#FF0000')
        else:
            self.current_page.error.text = 'successful'
            self.current_page.error.color = hex_color('#00FF00')

    def do_login(self):
        try:
            self.admin = admin_login(self.current_page.id_input.text, self.current_page.password_input.text)
        except Exception as exc:
            self.current_page.error.text = str(exc)
        else:
            self.load_ui('admin')

    def do_logout(self):
        self.admin = None
        self.load_ui('user')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_ui('user')

    def load_slide(self, cls_name):
        page = getattr(Factory, cls_name)()
        self.func_pages.load_slide(page)
        self.current_page = page

    def load_ui(self, mode):
        if mode == 'user':
            self.clear_widgets()
            self.current_list = Factory.UserFunctionList()
            self.func_pages = FuncPages()
            self.add_widget(self.current_list)
            self.add_widget(self.func_pages)
            self.load_slide('SearchBooks')
        elif mode == 'admin':
            self.clear_widgets()
            self.current_list = Factory.AdminFunctionList()
            self.func_pages = FuncPages()
            self.add_widget(self.current_list)
            self.add_widget(self.func_pages)
            self.load_slide('SearchBooks')


class FuncPages(BoxLayout):
    def load_slide(self, object):
        self.clear_widgets()
        self.add_widget(object)


class LibraryApp(App):
    def build(self):
        prepare_db()
        return LibraryRoot()


if __name__ == '__main__':
    from kivy.core.window import Window

    Window.clearcolor = hex_color('#FFFFFF')
    LibraryApp().run()
