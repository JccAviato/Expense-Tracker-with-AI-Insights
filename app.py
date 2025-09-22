#!/usr/bin/env python3
import os
from datetime import datetime, date
from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from ai import generate_insights, category_tips

Base = declarative_base()

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(64), nullable=False)
    merchant = Column(String(128), nullable=True)
    payment_method = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)

def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    db_path = os.environ.get("DATABASE_URL", "sqlite:///expense_tracker.db")
    app.config["DATABASE_URL"] = db_path

    # SQLAlchemy setup (no Flask-SQLAlchemy to keep deps minimal)
    engine = create_engine(db_path, echo=False, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # Utility to get a session per request
    def get_session():
        return Session()

    @app.context_processor
    def inject_now():
        return {"now": datetime.utcnow()}

    @app.route("/")
    def index():
        session = get_session()
        try:
            expenses = session.query(Expense).order_by(Expense.date.desc()).limit(10).all()
            totals = session.query(Expense).all()

            total_spend = sum(e.amount for e in totals)
            by_category = defaultdict(float)
            by_month = defaultdict(float)
            for e in totals:
                by_category[e.category] += e.amount
                ym = e.date.strftime("%Y-%m")
                by_month[ym] += e.amount

            categories = list(by_category.keys())
            cat_values = [round(by_category[c], 2) for c in categories]

            months_sorted = sorted(by_month.keys())
            month_values = [round(by_month[m], 2) for m in months_sorted]

            return render_template(
                "index.html",
                expenses=expenses,
                total_spend=round(total_spend, 2),
                categories=categories,
                cat_values=cat_values,
                months=months_sorted,
                month_values=month_values,
            )
        finally:
            session.close()

    @app.route("/expenses")
    def list_expenses():
        session = get_session()
        try:
            q = session.query(Expense)
            category = request.args.get("category", "").strip()
            start = request.args.get("start", "").strip()
            end = request.args.get("end", "").strip()
            if category:
                q = q.filter(Expense.category == category)
            if start:
                try:
                    d = datetime.strptime(start, "%Y-%m-%d").date()
                    q = q.filter(Expense.date >= d)
                except ValueError:
                    flash("Invalid start date format. Use YYYY-MM-DD.", "warning")
            if end:
                try:
                    d = datetime.strptime(end, "%Y-%m-%d").date()
                    q = q.filter(Expense.date <= d)
                except ValueError:
                    flash("Invalid end date format. Use YYYY-MM-DD.", "warning")

            expenses = q.order_by(Expense.date.desc(), Expense.id.desc()).all()
            total = round(sum(e.amount for e in expenses), 2)
            return render_template("expenses.html", expenses=expenses, total=total, category=category, start=start, end=end)
        finally:
            session.close()

    @app.route("/add", methods=["GET", "POST"])
    def add_expense():
        if request.method == "POST":
            session = get_session()
            try:
                date_str = request.form.get("date", "").strip()
                amount_str = request.form.get("amount", "").strip()
                category = request.form.get("category", "").strip() or "Other"
                merchant = request.form.get("merchant", "").strip() or None
                payment_method = request.form.get("payment_method", "").strip() or None
                notes = request.form.get("notes", "").strip() or None

                try:
                    d = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    flash("Invalid date. Use YYYY-MM-DD.", "danger")
                    return redirect(url_for("add_expense"))

                try:
                    amount = float(amount_str)
                    if amount <= 0:
                        raise ValueError("Amount must be positive.")
                except ValueError:
                    flash("Amount must be a positive number.", "danger")
                    return redirect(url_for("add_expense"))

                e = Expense(date=d, amount=amount, category=category, merchant=merchant,
                            payment_method=payment_method, notes=notes)
                session.add(e)
                session.commit()
                flash("Expense added!", "success")
                return redirect(url_for("list_expenses"))
            except SQLAlchemyError as err:
                session.rollback()
                flash(f"Database error: {err}", "danger")
            finally:
                session.close()
        # GET
        suggested_date = date.today().strftime("%Y-%m-%d")
        return render_template("add_expense.html", today=suggested_date)

    @app.route("/delete/<int:expense_id>", methods=["POST"])
    def delete_expense(expense_id):
        session = get_session()
        try:
            e = session.get(Expense, expense_id)
            if e:
                session.delete(e)
                session.commit()
                flash("Expense deleted.", "info")
            else:
                flash("Expense not found.", "warning")
        except SQLAlchemyError as err:
            session.rollback()
            flash(f"Database error: {err}", "danger")
        finally:
            session.close()
        return redirect(url_for("list_expenses"))

    @app.route("/insights")
    def insights():
        session = get_session()
        try:
            expenses = session.query(Expense).all()
            insights_data = generate_insights(expenses)
            return render_template("insights.html", insights=insights_data, category_tips=category_tips)
        finally:
            session.close()

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
