from model import *
from datetime import date

prepare_db()
admin = admin_login('roy', 'nopass')
admin.add_card(id='1', name='wjk', type='ta')
admin.add_book(id='1', title='db', price=2.35, total=3, stock=3)
return_date = date.today()
admin.borrow_book('1', '1', return_date)
borrowed_book = admin.list_borrows('1')
admin.add_book(id='4', title='数据库', price=2.35, total=3, stock=3)
admin.borrow_book('1', '2', return_date)
search_books(title='db', price=(3, 4)).fetchall()
admin.find_nearest_return(4)
