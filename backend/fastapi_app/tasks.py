from apscheduler.schedulers.background import BackgroundScheduler
from .routes import get_stock_price
from shared.models import StockPrice
from shared.database import get_db

scheduler = BackgroundScheduler()


def update_stock_prices():
    db = next(get_db())
    for stock in db.query(StockPrice).all():
        price = get_stock_price(stock.symbol)
        stock.price = price["price"]
        db.commit()
    db.close()


scheduler.add_job(
    id="update_stock_prices", func=update_stock_prices, trigger="interval", minutes=60
)
scheduler.start()
