from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, event, Numeric
from typing import Literal, Optional
import datetime
from decimal import Decimal
import sqlite3
from flask import g

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

"""
Tabelle
"""

# Utenti

class Utenti(db.Model):
  __tablename__ = 'Utenti'

  username: Mapped[str] = mapped_column(primary_key=True)
  password: Mapped[str]
  is_admin: Mapped[bool]

# Mercati

Giorno = Literal['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']

class Mercati(db.Model):
  __tablename__ = 'Mercati'

  nome: Mapped[str] = mapped_column(primary_key=True)
  giorno: Mapped[Giorno] = mapped_column(primary_key=True)
  is_evento: Mapped[bool]
  is_attuale: Mapped[Optional[bool]]

  __table_args__ = (
      CheckConstraint(
      "giorno IN ('Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica')",
      name='giorno_dominio'
    ),
    CheckConstraint(
      '(is_evento = 1 AND is_attuale IS NULL) OR (is_evento = 0 AND is_attuale IS NOT NULL)',
      name="check_is_attuale"
    ),
    CheckConstraint(
      "(is_attuale = 0 AND nome LIKE '%_old') OR (is_attuale IS NULL OR is_attuale != 0)",
      name="check_nome_old",
    )
  )

# Corrispettivi

class Corrispettivi(db.Model):
  __tablename__ = 'Corrispettivi'

  data: Mapped[datetime.date] = mapped_column(primary_key=True)
  mercato: Mapped[str] = mapped_column(primary_key=True)
  ts: Mapped[datetime.datetime] 
  inserito_da: Mapped[str]
  giorno_mercato: Mapped[Giorno]
  cassa: Mapped[str]
  reparto1: Mapped[Decimal] = mapped_column(Numeric(10, 2))
  reparto2: Mapped[Decimal] = mapped_column(Numeric(10, 2))
  reparto3: Mapped[Decimal] = mapped_column(Numeric(10, 2))
  reparto4: Mapped[Decimal] = mapped_column(Numeric(10, 2))
  reparto5: Mapped[Decimal] = mapped_column(Numeric(10, 2))
  quantita1: Mapped[int]
  quantita2: Mapped[int]
  quantita3: Mapped[int]
  quantita4: Mapped[int]
  quantita5: Mapped[int]

  __table_args__ =(
    ForeignKeyConstraint(
      ['inserito_da'], ['Utenti.username']
    ),
    ForeignKeyConstraint(
      ['mercato', 'giorno_mercato'], ['Mercati.nome', 'Mercati.giorno'],
      onupdate='CASCADE'
    ),
    CheckConstraint(
      'data <= ts',
      name="data_futura_check"
    ),
    CheckConstraint(
      'cassa GLOB "Cassa [1-9]"',
      name="cassa_check"
    ),
    CheckConstraint(
      'reparto1 >= 0',
      name='reparto1_non_negativo_check'
    ),
    CheckConstraint(
      'reparto2 >= 0',
      name='reparto2_non_negativo_check'
    ),
    CheckConstraint(
      'reparto3 >= 0',
      name='reparto3_non_negativo_check'
    ),
    CheckConstraint(
      'reparto4 >= 0',
      name='reparto4_non_negativo_check'
    ),
    CheckConstraint(
      'reparto5 >= 0',
      name='reparto5_non_negativo_check'
    ),
    CheckConstraint(
      'quantita1 >= 0',
      name='quantita1_non_negativo_check'
    ),
    CheckConstraint(
      'quantita2 >= 0',
      name='quantita2_non_negativo_check'
    ),
    CheckConstraint(
      'quantita3 >= 0',
      name='quantita3_non_negativo_check'
    ),
    CheckConstraint(
      'quantita4 >= 0',
      name='quantita4_non_negativo_check'
    ),
    CheckConstraint(
      'quantita5 >= 0',
      name='quantita5_non_negativo_check'
    )
  )

def init_db(app):
  db.init_app(app)

  with app.app_context():
    # attiviamo il vincolo di chiave esterna che in SQLite non è attivo di default
    @event.listens_for(db.engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
      if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    with db.engine.connect() as conn:
      res = conn.execute(db.text("PRAGMA foreign_keys")).scalar()
      print("FOREIGN KEYS ATTIVI:", res)  # Deve stampare 1
    
    db.drop_all()
    db.create_all()

    # popoliamo il database con dati di prova
    db.session.add_all([
      Utenti(
        username='Dario',
        password='pw',
        is_admin=True
      ),
      Utenti(
        username='Yuuki',
        password='pw',
        is_admin=False
      ),
      Mercati(
        nome='Centro',
        giorno='Sabato',
        is_evento=False,
        is_attuale=True
      ),
      Mercati(
        nome='Centro',
        giorno='Lunedì',
        is_evento=False,
        is_attuale=True
      ),
      Mercati(
        nome='Passons',
        giorno='Martedì',
        is_evento=False,
        is_attuale=True
      ),
      Mercati(
        nome='Centro_old',
        giorno='Martedì',
        is_evento=False,
        is_attuale=False
      ),
      Mercati(
        nome='Friuli DOC',
        giorno='Domenica',
        is_evento=True,
        is_attuale=None
      )
    ])
    db.session.commit()

  return db