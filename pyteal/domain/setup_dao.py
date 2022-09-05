from pyteal import *
from common.state import *
from common.constants import *
from common.general import *
from common.inner_txs import *

def dao_setup_init_global_state(args): return Seq(
    # initialize state
    set_gs(GLOBAL_RECEIVED_TOTAL, Int(0)),
    set_gs(GLOBAL_AVAILABLE_AMOUNT, Int(0)),
    set_gs(GLOBAL_LOCKED_SHARES, Int(0)),

    set_gs(GLOBAL_SHARES_ASSET_ID, Btoi(args[0])),
    set_gs(GLOBAL_FUNDS_ASSET_ID, Btoi(args[1])),

    set_gs(GLOBAL_DAO_NAME, args[2]),
    set_gs(GLOBAL_DAO_DESC, args[3]),
    set_gs(GLOBAL_SHARE_PRICE, Btoi(args[4])),
    set_gs(GLOBAL_INVESTORS_PART, Btoi(args[5])),

    set_gs(GLOBAL_SOCIAL_MEDIA_URL, args[6]),

    set_gs(GLOBAL_VERSIONS, args[7]),

    # for now commented: on one side backwards compatibility with tests,
    # on the other, maybe we want to make funding target (and date) optional, 
    # so the project can start immediately and raise funds indefinitely..
    # (not sure whether this is legally possible)
    # in any case: min funds target 0 and end date "now", makes it effectively optional 
    # (as this moves the project effectively in "funds successfully raised" state)
    # Assert(Btoi(args[8]) > Int(0)), # sanity check: there should be always a (positive) funding target

    set_gs(GLOBAL_TARGET, Btoi(args[8])),
    set_gs(GLOBAL_TARGET_END_DATE, Btoi(args[9])),

    set_gs(GLOBAL_SETUP_DATE, Btoi(args[10])),

    set_gs(GLOBAL_PROSPECTUS_URL, args[11]),
    set_gs(GLOBAL_PROSPECTUS_HASH, args[12]),

    set_gs(GLOBAL_RAISED, Int(0)),

    set_gs(GLOBAL_MIN_INVEST_AMOUNT, Btoi(args[13])),
    set_gs(GLOBAL_MAX_INVEST_AMOUNT, Btoi(args[14])),

    # team is set in team view, not during dao setup
    set_gs(GLOBAL_TEAM_URL, Bytes("")),

    # create image nft, is image url was passed
    If(is_args_length_res(Gtxn[1], 16))
        .Then(setup_image_nft(Gtxn[1].application_args[15]))
        # if no image nft, initialize state with empty values
        # we need this because we verify the global state length in the app
        # and it's more reliable to have a fixed length than a range
        .Else(
            Seq(
                set_gs(GLOBAL_IMAGE_URL, Bytes("")),
                set_gs(GLOBAL_IMAGE_ASSET_ID, Int(0))
            )
        ),
)
