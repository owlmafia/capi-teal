from pyteal import *
from common.state import *
from common.constants import *

def dao_update_set_state(args): return Seq(
    set_gs(GLOBAL_DAO_NAME, args[1]),
    set_gs(GLOBAL_DAO_DESC, args[2]),
    # for now price is immutable, simplifies funds reclaiming
    # set_gs(GLOBAL_SHARE_PRICE), Btoi(args[3])),
    set_gs(GLOBAL_SOCIAL_MEDIA_URL, args[3]),
    set_gs(GLOBAL_VERSIONS, args[4]),

    # for now shares asset, funds asset and investor's part not updatable - have to think about implications

    set_gs(GLOBAL_PROSPECTUS_URL, args[5]),
    set_gs(GLOBAL_PROSPECTUS_HASH, args[6]),

    set_gs(GLOBAL_MIN_INVEST_AMOUNT, Btoi(args[7])),
    set_gs(GLOBAL_MAX_INVEST_AMOUNT, Btoi(args[8])),
)
