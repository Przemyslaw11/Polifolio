def calculate_portfolio_value(stocks, obligations):
    stock_value = sum(stock['quantity'] * stock['price'] for stock in stocks)
    obligation_value = sum(obligation['value'] for obligation in obligations)
    return stock_value + obligation_value
