import io
import threading
import pandas as pd
import plotly.io as pio
import plotly.graph_objs as go
import opencryptobot.constants as con

from io import BytesIO
from pandas import DataFrame
from telegram import ParseMode
from coinmarketcap import Market
from opencryptobot.api.coingecko import CoinGecko
from opencryptobot.plugin import OpenCryptoPlugin


# TODO: Default from_cur should be fiat
class Chart(OpenCryptoPlugin):

    cg_coin_id = None
    cmc_coin_id = None

    def get_cmd(self):
        return "c"

    @OpenCryptoPlugin.send_typing
    @OpenCryptoPlugin.save_data
    def get_action(self, bot, update, args):
        time_frame = 3  # Days
        vs_ticker = "BTC"

        if not args:
            update.message.reply_text(
                text=f"Usage:\n{self.get_usage()}",
                parse_mode=ParseMode.MARKDOWN)
            return

        if "-" in args[0]:
            pair = args[0].split("-", 1)
            vs_ticker = pair[0]
            ticker = pair[1]
        else:
            ticker = args[0]

        if len(args) > 1 and args[1].isnumeric():
            time_frame = args[1]

        cg_thread = threading.Thread(target=self._get_cg_coin_id, args=[ticker])
        cmc_thread = threading.Thread(target=self._get_cmc_coin_id, args=[ticker])

        cg_thread.start()
        cmc_thread.start()

        cg_thread.join()

        market = CoinGecko().get_coin_market_chart_by_id(self.cg_coin_id, vs_ticker, time_frame)

        # Volume
        df_volume = DataFrame(market["total_volumes"], columns=["DateTime", "Volume"])
        df_volume["DateTime"] = pd.to_datetime(df_volume["DateTime"], unit="ms")
        volume = go.Scatter(
            x=df_volume.get("DateTime"),
            y=df_volume.get("Volume"),
            name="Volume"
        )

        # Price
        df_price = DataFrame(market["prices"], columns=["DateTime", "Price"])
        df_price["DateTime"] = pd.to_datetime(df_price["DateTime"], unit="ms")
        price = go.Scatter(
            x=df_price.get("DateTime"),
            y=df_price.get("Price"),
            yaxis="y2",
            name="Price",
            line=dict(
                color=("rgb(22, 96, 167)"),
                width=2
            )
        )

        cmc_thread.join()

        layout = go.Layout(
            images=[dict(
                source=f"{con.LOGO_URL_PARTIAL}{self.cmc_coin_id}.png",
                opacity=0.8,
                xref="paper", yref="paper",
                x=1.05, y=1,
                sizex=0.2, sizey=0.2,
                xanchor="right", yanchor="bottom"
            )],
            autosize=False,
            width=800,
            height=600,
            margin=go.layout.Margin(
                l=125,
                r=50,
                b=70,
                t=100,
                pad=4
            ),
            yaxis=dict(domain=[0, 0.20], ticksuffix="  "),
            yaxis2=dict(domain=[0.25, 1], ticksuffix="  "),
            title=f"{vs_ticker.upper()} - {ticker.upper()}",
            legend=dict(orientation="h", yanchor="top", xanchor="center", y=1.05, x=0.45),
            shapes=[{
                "type": "line",
                "xref": "paper",
                "yref": "y2",
                "x0": 0,
                "x1": 1,
                "y0": market["prices"][len(market["prices"]) - 1][1],
                "y1": market["prices"][len(market["prices"]) - 1][1],
                "line": {
                    "color": "rgb(50, 171, 96)",
                    "width": 1,
                    "dash": "dot"
                }
            }],
        )

        fig = go.Figure(data=[price, volume], layout=layout)
        fig["layout"]["yaxis2"].update(tickformat="0.8f")

        update.message.reply_photo(
            photo=io.BufferedReader(BytesIO(pio.to_image(fig, format="webp"))),
            parse_mode=ParseMode.MARKDOWN)

    def get_usage(self):
        return "`/c [COIN] ([TIMEFRAME-IN-DAYS])`"

    def get_description(self):
        return "Show a graph for the given coin with price and volume"

    def _get_cg_coin_id(self, ticker):
        for coin in CoinGecko().get_coins_list():
            if coin["symbol"].lower() == ticker.lower():
                self.cg_coin_id = coin["id"]
                break

    def _get_cmc_coin_id(self, ticker):
        for listing in Market().listings()["data"]:
            if ticker.upper() == listing["symbol"].upper():
                self.cmc_coin_id = listing["id"]
                break
