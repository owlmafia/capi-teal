from pyteal import *
from common.constants import *
from common.state import *

# extracted part of claimable_dividend, for readability
# how much the investor is entitled to, based on the total received and the investor's locked shares (does not consider already claimed dividend)
def calc_total_entitled_dividend(investor): return Div(
    Mul(
        Div(
            Mul(
                Mul(App.localGet(investor, Bytes(LOCAL_SHARES)), tmpl_precision),
                tmpl_investors_share
            ),
            tmpl_share_supply
        ),
        get_gs(GLOBAL_RECEIVED_TOTAL)
    ),
    tmpl_precision_square
)

# Calculates claimable dividend based on LOCAL_SHARES and LOCAL_CLAIMED_TOTAL.
# Expects claimer to be the gtxn 0 sender.
def calc_claimable_dividend(investor): return Minus(
    calc_total_entitled_dividend(investor), 
    App.localGet(investor, Bytes(LOCAL_CLAIMED_TOTAL))
)
