from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, CheckConstraint, create_engine
from sqlalchemy import select, and_, desc, func
from sqlalchemy.types import *
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.exc import IntegrityError
from datetime import date
from collections import abc
from functools import reduce
import csv

__all__ = [
    # db objects
    'engine', 'Base', 'session',
    # functions
    'prepare_db', 'search_books', 'admin_login', 'desc',
    # classes
    'Book', 'Card', 'Admin', 'Borrow',
    # tables
    'books', 'cards', 'admins', 'borrows',
    # exceptions
    'NotFoundError', 'ForbiddenOperationError', 'VerificationError']

engine = create_engine('mysql+pymysql://root:nopass@localhost:3306/library?charset=utf8mb4')
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()


# exceptions

class NotFoundError(Exception):
    pass


class ForbiddenOperationError(Exception):
    pass


class VerificationError(Exception):
    pass


# functions

def prepare_db():
    if not database_exists(engine.url):
        create_database(engine.url)
    Base.metadata.create_all(engine)


def search_books(type=None, title=None, publisher=None, year=None, author=None, price=None, order_by=None):
    stmt = select([books])
    criteria = []
    if type:
        criteria.append(books.c.type == type)
    if title:
        criteria.append(books.c.title == title)
    if publisher:
        criteria.append(books.c.publisher == publisher)
    if year:
        if isinstance(year, abc.Sequence):
            start_year, end_year = year
            criteria.append(books.c.year.between(start_year, end_year))
        else:
            criteria.append(books.c.year == year)
    if author:
        criteria.append(books.c.author == author)
    if price:
        if isinstance(price, abc.Sequence):
            start_price, end_price = price
            criteria.append(books.c.price.between(start_price, end_price))
        else:
            criteria.append(books.c.price == price)
    if criteria:
        stmt = stmt.where(reduce(and_, criteria))
    if order_by is not None:
        if isinstance(order_by, abc.Sequence):
            stmt = stmt.order_by(*order_by)
        else:
            stmt = stmt.order_by(order_by)
    with engine.connect() as connection:
        rp = connection.execute(stmt)
        return rp


def admin_login(id, password):
    admin = session.query(Admin).filter(Admin.id == id).first()
    if admin is None:
        raise NotFoundError('admin with id {!r} not found'.format(id))
    else:
        if admin.password == password:
            return admin
        else:
            raise VerificationError('incorrect password for admin with id {!r}'.format(id))


def CSVWrapper(file):
    for line in file.readlines():
        yield line.lstrip('( ').rstrip(') \n')


# classes

class Book(Base):
    __tablename__ = 'books'
    __table_args__ = (CheckConstraint('price>=0', name='price_non_negative'),
                      CheckConstraint('total>=0', name='total_non_negative'),
                      CheckConstraint('stock>=0', name='stock_non_negative'))

    id = Column(String(50), primary_key=True)
    type = Column(String(20))
    title = Column(String(50), nullable=False)
    publisher = Column(String(50))
    year = Column(Integer())
    author = Column(String(50))
    price = Column(Numeric(10, 2), nullable=False)
    total = Column(Integer(), nullable=False)
    stock = Column(Integer(), nullable=False, default=total)
    borrow_records = relationship('Borrow')


books = Book.__table__


class Admin(Base):
    __tablename__ = 'admins'

    id = Column(String(50), primary_key=True)
    password = Column(String(50), nullable=False)
    name = Column(String(50), nullable=False)
    contact = Column(String(50), nullable=False)
    borrow_records = relationship('Borrow')

    @staticmethod
    def add_book(**kwargs):
        book = Book(**kwargs)
        try:
            session.add(book)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ForbiddenOperationError(exc.orig)

    def import_books(self, file_path):
        attrs = ['id',
                 'type',
                 'title',
                 'publisher',
                 'year',
                 'author',
                 'price',
                 'total',
                 ]
        with open(file_path) as file:
            wrapped_file = CSVWrapper(file)
            reader = csv.reader(wrapped_file)
            try:
                for row in reader:
                    params = {key: value for key, value in zip(attrs, row)}
                    session.add(Book(**params))
                session.commit()
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def list_borrows(card_id):
        card = session.query(Card).filter(Card.id == card_id).first()
        if card is None:
            raise NotFoundError('card with id {!r} not found'.format(card_id))
        else:
            # return card.borrowed_books
            # return session.query(Book).join(Borrow).join(Card).filter(Card.id == card.id).all()
            stmt = select([books.c.id,
                           books.c.type,
                           books.c.title,
                           books.c.publisher,
                           books.c.year,
                           books.c.author,
                           books.c.price,
                           books.c.total,
                           books.c.stock
                           ]).select_from(books.join(borrows).join(cards)).where(cards.c.id == card.id)

            with engine.connect() as connection:
                rp = connection.execute(stmt)
                return rp.fetchall()

    def borrow_book(self, card_id, book_id, return_date):
        book = session.query(Book).filter(Book.id == book_id).first()
        card = session.query(Card).filter(Card.id == card_id).first()
        if book is None:  # wrap IntegrityError for foreign keys into ValueError here
            raise NotFoundError('book with id {!r} not found'.format(book_id))
        if card is None:
            raise NotFoundError('card with id {!r} not found'.format(card_id))
        if return_date < date.today():
            raise ValueError('return date before today')
        else:
            if book.stock > 0:
                book.stock -= 1
                record = Borrow(card_id=card_id,
                                book_id=book_id,
                                admin_id=self.id,
                                return_date=return_date)
                session.add(record)
                session.commit()
            else:
                raise ForbiddenOperationError('not enough books for book with id {!r}'.format(book_id))
                # try:
                #     book.stock -= 1
                #     record = Borrow(card_id=card_id,
                #                     book_id=book_id,
                #                     admin_id=self.id,
                #                     return_date=return_date)
                #     session.add(record)
                #     session.commit()
                # except IntegrityError as exc:
                #     session.rollback()
                #     raise ForbiddenOperationError(exc.orig)

    @staticmethod
    def find_nearest_return(book_id):
        stmt = select([func.min(borrows.c.return_date).label('return_date')]).where(borrows.c.book_id == book_id)
        with engine.connect() as connection:
            record = connection.execute(stmt).first()
            if record is None:
                raise NotFoundError("book with id {!r} doesn't exist or haven't been borrowed".format(book_id))
            else:
                return record.return_date

    @staticmethod
    def return_book(card_id, book_id):
        book = session.query(Book).filter(Book.id == book_id).first()
        if book is None:
            raise NotFoundError('book with id {!r} not found'.format(book_id))
        record = session.query(Borrow).filter((Borrow.card_id == card_id)
                                              & (Borrow.book_id == book_id)).first()
        if record is None:
            raise NotFoundError('record with card id {!r} borrowing book id {!r} not found'.format(card_id, book_id))
        else:
            book.stock += 1
            session.delete(record)
            session.commit()

    @staticmethod
    def add_card(**kwargs):
        card = Card(**kwargs)
        try:
            session.add(card)
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ForbiddenOperationError(exc.orig)

    @staticmethod
    def remove_card(card_id):
        card = session.query(Card).filter(Card.id == card_id).first()
        if card is None:
            raise NotFoundError('card with id {!r} not found'.format(card_id))
        else:
            try:
                session.delete(card)
                session.commit()
            except Exception as exc:
                session.rollback()
                raise


admins = Admin.__table__


class Borrow(Base):
    __tablename__ = 'borrows'
    __table_args__ = CheckConstraint('return_date > borrow_date', name='valid_return_date'),

    id = Column(Integer(), primary_key=True)
    card_id = Column(ForeignKey('cards.id'), nullable=False, index=True)
    book_id = Column(ForeignKey('books.id'), nullable=False, index=True)
    borrow_date = Column(Date(), nullable=False, default=date.today)
    return_date = Column(Date(), nullable=False)
    admin_id = Column(ForeignKey('admins.id'), nullable=False)


borrows = Borrow.__table__


class Card(Base):
    __tablename__ = 'cards'

    id = Column(String(50), primary_key=True)
    name = Column(String(50), nullable=False)
    dept = Column(String(50))
    type = Column(String(20), nullable=False)
    borrow_records = relationship('Borrow')
    borrowed_books = relationship('Book', secondary=borrows, uselist=True)


cards = Card.__table__
