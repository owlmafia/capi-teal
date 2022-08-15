from pyteal import *
from functions.app_call_checks import *
from functions.asset_checks import *

"""App central approval"""

tmpl_share_price = Tmpl.Int("TMPL_SHARE_PRICE")
tmpl_capi_escrow_address = Tmpl.Addr("TMPL_CAPI_ESCROW_ADDRESS")
# note "__" at the end so text isn't contained in TMPL_PRECISION_SQUARE
tmpl_precision = Tmpl.Int("TMPL_PRECISION__")
tmpl_capi_share = Tmpl.Int("TMPL_CAPI_SHARE")
tmpl_precision_square = Tmpl.Int("TMPL_PRECISION_SQUARE")
tmpl_investors_share = Tmpl.Int("TMPL_INVESTORS_SHARE")
tmpl_share_supply = Tmpl.Int("TMPL_SHARE_SUPPLY")
tmpl_max_raisable_amount = Tmpl.Int("TMPL_MAX_RAISABLE_AMOUNT")

GLOBAL_RECEIVED_TOTAL = "CentralReceivedTotal"
GLOBAL_AVAILABLE_AMOUNT = "AvailableAmount"

GLOBAL_SHARES_ASSET_ID = "SharesAssetId"
GLOBAL_FUNDS_ASSET_ID = "FundsAssetId"

GLOBAL_LOCKED_SHARES = "LockedShares"

GLOBAL_DAO_NAME = "DaoName"
GLOBAL_DAO_DESC = "DaoDesc"
GLOBAL_SHARE_PRICE = "SharePrice"
# % of income directed to investors
GLOBAL_INVESTORS_PART = "InvestorsPart"

GLOBAL_SOCIAL_MEDIA_URL = "SocialMediaUrl"

GLOBAL_TARGET = "Target"
# Date where the dao was setup
# it's likely possible to get this via indexer, instead of storing it in teal
# but for now this seems fine - it's just 4 more lines in TEAL, less requests when loading a dao, and quicker to implement.
GLOBAL_SETUP_DATE = "SetupDate"
GLOBAL_TARGET_END_DATE = "TargetEndDate"
GLOBAL_RAISED = "Raised"

GLOBAL_IMAGE_ASSET_ID = "ImageAsset"
GLOBAL_IMAGE_URL = "ImageUrl"
# can be an empty string (equivalent to "none")
# note that this is handled different than the image url - for the later,
# we make it actually optional, to more easily detect here that it's not set and not create the NFT.
GLOBAL_PROSPECTUS_URL = "ProspectusUrl"
GLOBAL_PROSPECTUS_HASH = "ProspectusHash"

GLOBAL_VERSIONS = "Versions"

GLOBAL_MIN_INVEST_AMOUNT = "GlobalMinInvestAmount"
GLOBAL_MAX_INVEST_AMOUNT = "GlobalMaxInvestAmount"

LOCAL_SHARES = "Shares"
LOCAL_CLAIMED_TOTAL = "ClaimedTotal"
LOCAL_CLAIMED_INIT = "ClaimedInit"

# Prospectus acknowledged by investor, when investing
# Note: investor can store (by means other than our app) an inconsistent url-hash (teal can't prove this)
# but they're not incentivized to do this: anyone can prove that the combination is invalid
# as the url contains an IPFS CID which is also a hash of the document
# (if the document that corresponds to the url/CID can't be hashed to our hash, it's invalid)
# Note: we need a hash additionally to the CID, because the CID algorithm is IPFS specific and it's unclear how it works exactly
LOCAL_SIGNED_PROSPECTUS_URL= "SignedProspectusUrl"
LOCAL_SIGNED_PROSPECTUS_HASH= "SignedProspectusHash"
LOCAL_SIGNED_PROSPECTUS_TIMESTAMP= "SignedProspectusTimestamp"

def approval_program():
    handle_create = Seq(
        Approve()
    )

    handle_update = Seq(
        Assert(Global.group_size() == Int(1)),

        is_app_call_by_creator(Gtxn[0]),

        Approve()
    )

    def setup_image_nft(url_bytes):
        return Seq(
            App.globalPut(Bytes(GLOBAL_IMAGE_URL), url_bytes),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.asset_amount: Int(0),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_total: Int(1),
                TxnField.config_asset_manager: Gtxn[0].sender(),
                TxnField.config_asset_default_frozen: Int(0),
                TxnField.config_asset_unit_name: Bytes("IMG"),
                TxnField.config_asset_name: Bytes("IMG"),
                TxnField.config_asset_url: url_bytes,
                TxnField.fee: Int(0)
            }),
            InnerTxnBuilder.Submit(),
            App.globalPut(Bytes(GLOBAL_IMAGE_ASSET_ID), InnerTxn.created_asset_id())
        )
        
    handle_setup_dao = Seq(
        # creator sends min balance to app address
        Assert(Gtxn[0].type_enum() == TxnType.Payment),
        Assert(Gtxn[0].receiver() == Global.current_application_address()),

        # app call
        is_app_call_noop_this_app_by_creator(Gtxn[1]),
        Assert(Or(
            Gtxn[1].application_args.length() == Int(15), 
            Gtxn[1].application_args.length() == Int(16)
        )),

        # creator transfers shares (to be sold to investors) to app escrow
        is_asset_transfer(Gtxn[2]),
        # the asset transferred is what will be stored as shares asset id
        Assert(Gtxn[2].xfer_asset() == Btoi(Gtxn[1].application_args[0])),

        # initialize state
        App.globalPut(Bytes(GLOBAL_RECEIVED_TOTAL), Int(0)),
        App.globalPut(Bytes(GLOBAL_AVAILABLE_AMOUNT), Int(0)),
        App.globalPut(Bytes(GLOBAL_LOCKED_SHARES), Int(0)),

        App.globalPut(Bytes(GLOBAL_SHARES_ASSET_ID), Btoi(Gtxn[1].application_args[0])),
        App.globalPut(Bytes(GLOBAL_FUNDS_ASSET_ID), Btoi(Gtxn[1].application_args[1])),

        App.globalPut(Bytes(GLOBAL_DAO_NAME), Gtxn[1].application_args[2]),
        App.globalPut(Bytes(GLOBAL_DAO_DESC), Gtxn[1].application_args[3]),
        App.globalPut(Bytes(GLOBAL_SHARE_PRICE), Btoi(Gtxn[1].application_args[4])),
        App.globalPut(Bytes(GLOBAL_INVESTORS_PART), Btoi(Gtxn[1].application_args[5])),

        App.globalPut(Bytes(GLOBAL_SOCIAL_MEDIA_URL), Gtxn[1].application_args[6]),

        App.globalPut(Bytes(GLOBAL_VERSIONS), Gtxn[1].application_args[7]),

        # for now commented: on one side backwards compatibility with tests,
        # on the other, maybe we want to make funding target (and date) optional, 
        # so the project can start immediately and raise funds indefinitely..
        # (not sure whether this is legally possible)
        # in any case: min funds target 0 and end date "now", makes it effectively optional 
        # (as this moves the project effectively in "funds successfully raised" state)
        # Assert(Btoi(Gtxn[1].application_args[8]) > Int(0)), # sanity check: there should be always a (positive) funding target

        App.globalPut(Bytes(GLOBAL_TARGET), Btoi(Gtxn[1].application_args[8])),
        App.globalPut(Bytes(GLOBAL_TARGET_END_DATE), Btoi(Gtxn[1].application_args[9])),

        App.globalPut(Bytes(GLOBAL_SETUP_DATE), Btoi(Gtxn[1].application_args[10])),

        App.globalPut(Bytes(GLOBAL_PROSPECTUS_URL), Gtxn[1].application_args[11]),
        App.globalPut(Bytes(GLOBAL_PROSPECTUS_HASH), Gtxn[1].application_args[12]),

        App.globalPut(Bytes(GLOBAL_RAISED), Int(0)),

        App.globalPut(Bytes(GLOBAL_MIN_INVEST_AMOUNT), Btoi(Gtxn[1].application_args[13])),
        App.globalPut(Bytes(GLOBAL_MAX_INVEST_AMOUNT), Btoi(Gtxn[1].application_args[14])),


        # checks depending on global state

        Assert(Gtxn[2].xfer_asset() == App.globalGet(Bytes(GLOBAL_SHARES_ASSET_ID))),

        # create image nft, is image url was passed
        If(Gtxn[1].application_args.length() == Int(16))
            .Then(setup_image_nft(Gtxn[1].application_args[15]))
            # if no image nft, initialize state with empty values
            # we need this because we verify the global state length in the app
            # and it's more reliable to have a fixed length than a range
            .Else(
                Seq(
                    App.globalPut(Bytes(GLOBAL_IMAGE_URL), Bytes("")),
                    App.globalPut(Bytes(GLOBAL_IMAGE_ASSET_ID), Int(0))
                )
            ),

        # creator's account setup

        InnerTxnBuilder.Begin(),
        # optin to funds asset
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_receiver: Global.current_application_address(),
            TxnField.asset_amount: Int(0),
            TxnField.xfer_asset: App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID)),
            TxnField.fee: Int(0)
        }),
        InnerTxnBuilder.Next(),
        # optin to shares asset
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_receiver: Global.current_application_address(),
            TxnField.asset_amount: Int(0),
            TxnField.xfer_asset: App.globalGet(Bytes(GLOBAL_SHARES_ASSET_ID)),
            TxnField.fee: Int(0)
        }),
        InnerTxnBuilder.Submit(),

        Approve()
    )

    def handle_update_data_tx(tx):
        return Seq(
            # app call
            is_app_call_noop_this_app_by_creator(tx),

            # update data
            App.globalPut(Bytes(GLOBAL_DAO_NAME), tx.application_args[1]),
            App.globalPut(Bytes(GLOBAL_DAO_DESC), tx.application_args[2]),
            # for now price is immutable, simplifies funds reclaiming
            # App.globalPut(Bytes(GLOBAL_SHARE_PRICE), Btoi(tx.application_args[3])),
            App.globalPut(Bytes(GLOBAL_SOCIAL_MEDIA_URL), tx.application_args[3]),
            App.globalPut(Bytes(GLOBAL_VERSIONS), tx.application_args[4]),

            # for now shares asset, funds asset and investor's part not updatable - have to think about implications

            App.globalPut(Bytes(GLOBAL_PROSPECTUS_URL), tx.application_args[5]),
            App.globalPut(Bytes(GLOBAL_PROSPECTUS_HASH), tx.application_args[6]),

            App.globalPut(Bytes(GLOBAL_MIN_INVEST_AMOUNT), Btoi(tx.application_args[7])),
            App.globalPut(Bytes(GLOBAL_MAX_INVEST_AMOUNT), Btoi(tx.application_args[8])),
        )

    handle_update_data_basic = Seq(
        handle_update_data_tx(Gtxn[0]),
        # handle_update_data_common,

        Assert(Global.group_size() == Int(1)),

        Assert(Gtxn[0].application_args.length() == Int(9)),

        Approve()
    )

    handle_update_data_with_image = Seq(
        handle_update_data_tx(Gtxn[1]),

        # group size checked in cond

        # increase min balance to hold new nft
        Assert(Gtxn[0].type_enum() == TxnType.Payment),
        Assert(Gtxn[0].receiver() == Global.current_application_address()),

        # the first tx is the payment to increase min balance, to be able to hold an additional asset
        Assert(Gtxn[1].application_args[0] == Bytes("update_data")),
        Assert(Gtxn[1].application_args.length() == Int(10)),

        If(App.globalGet(Bytes(GLOBAL_IMAGE_URL)) != Gtxn[1].application_args[9])
            .Then(setup_image_nft(Gtxn[1].application_args[9])),

        Approve()
    )

    handle_optin = Seq(
        Assert(Global.group_size() == Int(1)),

        is_this_app_call(Gtxn[0]),
        Assert(Gtxn[0].on_completion() == OnComplete.OptIn),

        # initialize local state with default values
        # why: for general sanity, our app checks always for expected local state length
        # if investor interrups the investing flow after opting in, local state length will be 0
        # and the app will throw an error when reading it
        # we might remove these checks later, in which case this initialization can be removed
        # we'll keep them for now, at least until ready for a security audit
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SHARES), Int(0)),
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_CLAIMED_TOTAL), Int(0)),
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_CLAIMED_INIT), Int(0)),
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_URL), Bytes("")),
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_HASH), Bytes("")),
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_TIMESTAMP), Bytes("")),

        Approve()
    )

    handle_unlock = Seq(
        Assert(Global.group_size() == Int(1)),

        # app call to opt-out
        is_this_app_call(Gtxn[0]),
        Assert(Gtxn[0].on_completion() == OnComplete.CloseOut),

        # shares xfer to the investor
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_receiver: Gtxn[0].sender(),
            TxnField.asset_amount: App.localGet(Gtxn[0].sender(), Bytes(LOCAL_SHARES)),
            TxnField.xfer_asset: App.globalGet(Bytes(GLOBAL_SHARES_ASSET_ID)),
            TxnField.fee: Int(0)
        }),
        InnerTxnBuilder.Submit(),

        # Don't allow to unlock until fund raising period ended.
        # We need this to be able to set a max limit to shares that can be bought
        # (that is, during the funds raising period, 
        # it's still unclear, for legal and UX reasons, what to do in the time after, including whether it should be possible to invest at all (currently it is)).
        # If the investor can't unlock, we can check the total shares in local state to prevent buying.
        # If the investor were to be able to unlock, we wouldn't have anything to add to
        # (note that asset balance doesn't work either, as after unlocking the user can transfer the shares to another account).
        Assert(Global.latest_timestamp() > App.globalGet(Bytes(GLOBAL_TARGET_END_DATE))),        

        # TODO where is locked shares local state decremented? not tested?

        # decrement locked shares global state
        App.globalPut(
            Bytes(GLOBAL_LOCKED_SHARES),
            Minus(
                App.globalGet(Bytes(GLOBAL_LOCKED_SHARES)),
                App.localGet(Gtxn[0].sender(), Bytes(LOCAL_SHARES))
            )
        ),

        Approve()
    )

    # extracted part of claimable_dividend, for readability
    # how much the investor is entitled to, based on the total received and the investor's locked shares (does not consider already claimed dividend)
    total_entitled_dividend = Div(
        Mul(
            Div(
                Mul(
                    Mul(App.localGet(Gtxn[0].sender(), Bytes(LOCAL_SHARES)), tmpl_precision),
                    tmpl_investors_share
                ),
                tmpl_share_supply
            ),
            App.globalGet(Bytes(GLOBAL_RECEIVED_TOTAL))
        ),
        tmpl_precision_square
    )

    # Calculates claimable dividend based on LOCAL_SHARES and LOCAL_CLAIMED_TOTAL.
    # Expects claimer to be the gtxn 0 sender.
    claimable_dividend = Minus(
        total_entitled_dividend, 
        App.localGet(Gtxn[0].sender(), Bytes(LOCAL_CLAIMED_TOTAL))
    )

    handle_claim = Seq(
        Assert(Global.group_size() == Int(1)),

        # app call
        is_this_noop_app_call(Gtxn[0]),
        
        #TODO tests: can't withdraw and claim more than available amount

        # has to be <= available amount
        Assert(claimable_dividend <= App.globalGet(Bytes(GLOBAL_AVAILABLE_AMOUNT))),

        # send dividend to caller
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            # todo scratch? compare teal length with repeating claimable_dividend
            TxnField.asset_amount: claimable_dividend,
            TxnField.asset_receiver: Gtxn[0].sender(),
            TxnField.xfer_asset: App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID)),
        }),
        InnerTxnBuilder.Submit(),

        # decrease available amount
        # no underflow possible, since we checked that claimable_dividend <= GLOBAL_AVAILABLE_AMOUNT
        # NOTE: BEFORE updating LOCAL_CLAIMED_TOTAL, since we read it to calculate the current divident being claimed
        # (TODO above solved by using scratch?)
        App.globalPut(
            Bytes(GLOBAL_AVAILABLE_AMOUNT),
            Minus(
                App.globalGet(Bytes(GLOBAL_AVAILABLE_AMOUNT)),
                claimable_dividend
            )
        ),

        # update local state with retrieved dividend
        App.localPut(
            Gtxn[0].sender(),
            Bytes(LOCAL_CLAIMED_TOTAL),
            Add(
                App.localGet(Gtxn[0].sender(), Bytes(LOCAL_CLAIMED_TOTAL)),
                claimable_dividend
            )
        ),

        Approve()
    )

    # expects tx 1 to be the shares xfer to the app and its sender verified as app caller (local state)
    @Subroutine(TealType.none)
    def lock_shares(share_amount, sender):
        claimable_before_locking = ScratchVar(TealType.uint64)

        return Seq(
            claimable_before_locking.store(claimable_dividend),

            App.localPut(  # set / increment share count in local state
                sender,
                Bytes(LOCAL_SHARES),
                Add(
                    App.localGet(sender, Bytes(LOCAL_SHARES)),
                    share_amount
                )
            ),

            # initialize already claimed local state
            App.localPut(
                sender,
                Bytes(LOCAL_CLAIMED_TOTAL),
                Minus(claimable_dividend, claimable_before_locking.load())
            ),
            
            # remember initial already claimed local state
            App.localPut(
                sender,
                Bytes(LOCAL_CLAIMED_INIT),
                App.localGet(sender, Bytes(LOCAL_CLAIMED_TOTAL))
            ),

            # increment locked shares global state
            App.globalPut(
                Bytes(GLOBAL_LOCKED_SHARES),
                Add(App.globalGet(Bytes(GLOBAL_LOCKED_SHARES)), share_amount)
            ),
        )

    handle_lock = Seq(
        # app call to update state
        is_this_noop_app_call(Gtxn[0]),
        Assert(Gtxn[0].application_args.length() == Int(4)),

        # shares xfer to app
        is_shares_transfer(Gtxn[1]),
        Assert(Gtxn[1].asset_receiver() == Global.current_application_address()),
        Assert(Gtxn[1].asset_amount() > Int(0)),

        # app caller is locking the shares
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),

        # save shares on local state
        lock_shares(Gtxn[1].asset_amount(), Gtxn[0].sender()),

        # save acked prospectus
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_URL), Gtxn[0].application_args[1]),
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_HASH), Gtxn[0].application_args[2]),
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_TIMESTAMP), Gtxn[0].application_args[3]),

        Approve()
    )

    app_escrow_funds_balance = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID))
    )

    # funds that are on the app's balance but haven't been drained (made available) yet
    # note that withdrawals don't affect this value, 
    # as they're substracted atomically (in the withdrawal group) from both balance and GLOBAL_AVAILABLE_AMOUNT
    # so basic arithmetic: if we substract a value from both operands of a substraction, the result is unaffected
    handle_drain_not_yet_drained_amount = Minus(
        app_escrow_funds_balance.value(),
        App.globalGet(Bytes(GLOBAL_AVAILABLE_AMOUNT))
    )

    def calculate_capi_fee(amount): 
        return Div(
            Mul(
                Mul(amount, tmpl_precision),
                tmpl_capi_share
            ),
            tmpl_precision_square
        )

    # handle_drain_capi_fee = ScratchVar(TealType.uint64)
    handle_drain = Seq(
        # handle_drain_capi_fee.store(calculate_capi_fee(handle_drain_not_yet_drained_amount)),
        
        Assert(Global.group_size() == Int(1)),

        # app call
        is_this_noop_app_call(Gtxn[0]),

        # needs to be listed like this, see: https://forum.algorand.org/t/using-global-get-ex-on-noop-call-giving-error-when-deploying-app/5314/2
        # (app_escrow_funds_balance is used in handle_drain_not_yet_drained_amount)
        app_escrow_funds_balance,

        # increment total received
        App.globalPut(
            Bytes(GLOBAL_RECEIVED_TOTAL),
            Add(
                App.globalGet(Bytes(GLOBAL_RECEIVED_TOTAL)),
                Minus(handle_drain_not_yet_drained_amount, calculate_capi_fee(handle_drain_not_yet_drained_amount))
            )
        ),

        # pay capi fee
        # note BEFORE updating GLOBAL_AVAILABLE_AMOUNT as it needs this state 
        # to calculate not yet drained amount  
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_amount: calculate_capi_fee(handle_drain_not_yet_drained_amount),
            TxnField.asset_receiver: tmpl_capi_escrow_address,
            TxnField.xfer_asset: App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID)),
        }),
        InnerTxnBuilder.Submit(),

        # increment available amount
        # WA = WA + NYD (not yet drained) - fee on NYD
        # in words: by draining we make the "new income" (in prev. implementation, customer escrow balance) minus capi fee available to be withdrawn
        # note AFTER the inner tx, 
        # which accesses GLOBAL_AVAILABLE_AMOUNT to calculate the not yet drained amount / the capi fee
        App.globalPut(
            Bytes(GLOBAL_AVAILABLE_AMOUNT),
            Add(
                App.globalGet(Bytes(GLOBAL_AVAILABLE_AMOUNT)),
                Minus(handle_drain_not_yet_drained_amount, calculate_capi_fee(handle_drain_not_yet_drained_amount))
            )
        ),

        Approve()
    )

    app_shares_balance = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(Bytes(GLOBAL_SHARES_ASSET_ID))
    )

    handle_invest_calculated_share_amount = ScratchVar(TealType.uint64)
    # note that when investing (opposed to locking, where there's a shares xfer), 
    # the share amount is calculated here (based on sent funds and share price)
    handle_invest = Seq(
        # Assert(Global.group_size() == Int(3)), # used as condition

        # investor opts-in to shares (needs to be before app call with inner tx sending the asset)
        # optin to shares
        is_shares_transfer(Gtxn[0]),
        Assert(Gtxn[0].asset_amount() == Int(0)),
        Assert(Gtxn[0].asset_receiver() == Gtxn[0].sender()),

        # app call to initialize shares state
        is_this_noop_app_call(Gtxn[1]),
        Assert(Gtxn[1].application_args.length() == Int(5)),

        # investor pays for shares: funds xfer to app escrow
        is_funds_transfer(Gtxn[2]),
        Assert(Gtxn[2].asset_amount() > Int(0)),
        Assert(Gtxn[2].asset_receiver() == Global.current_application_address()),

        # increment available amount state
        # investments don't pay capi fee or generate dividend, so are immediately available (don't have to be drained)
        App.globalPut(
            Bytes(GLOBAL_AVAILABLE_AMOUNT),
            Add(
                App.globalGet(Bytes(GLOBAL_AVAILABLE_AMOUNT)),
                Gtxn[2].asset_amount()
            )
        ),

        # the investor sends all txs
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),
        Assert(Gtxn[1].sender() == Gtxn[2].sender()),

        # save the calculated share amount in scratch (used in multiple places)
        handle_invest_calculated_share_amount.store(Div(Gtxn[2].asset_amount(), tmpl_share_price)),

        # double-check that the share amount matches what the caller expects
        # (just in case for unexpected rounding issues)
        Assert(handle_invest_calculated_share_amount.load() == Btoi(Gtxn[1].application_args[1])),

        # sanity check: the bought share amount is > 0 (even if for whatever reason 0 was passed as expected/argument)
        Assert(handle_invest_calculated_share_amount.load() > Int(0)),

        # needs to be listed like this, see: https://forum.algorand.org/t/using-global-get-ex-on-noop-call-giving-error-when-deploying-app/5314/2
        # (app_escrow_funds_balance is used in handle_drain_not_yet_drained_amount)
        app_shares_balance,

        # the bought share amount is <= shares for sale (balance - locked -> not locked, i.e. available for sale)
        Assert(handle_invest_calculated_share_amount.load() <= Minus(
            app_shares_balance.value(),
            App.globalGet(Bytes(GLOBAL_LOCKED_SHARES))
        )),

        # update total raised amount
        App.globalPut(Bytes(GLOBAL_RAISED), Add(
            App.globalGet(Bytes(GLOBAL_RAISED)),
            Gtxn[2].asset_amount()
        )),

        # total raised is below or equal to max allowed amount (regulatory)
        Assert(handle_invest_calculated_share_amount.load() <= tmpl_max_raisable_amount),

        # is investing more than min amount (share amount)
        Assert(handle_invest_calculated_share_amount.load() >= App.globalGet(Bytes(GLOBAL_MIN_INVEST_AMOUNT))),

        # save shares on local state
        lock_shares(
            handle_invest_calculated_share_amount.load(),
            Gtxn[0].sender()
        ),

        # has invested (is investing + possibly has invested before) less or same than max amount (share amount) 
        # NOTE this check has to be AFTER lock_shares, as it expects LOCAL_SHARES to be incremented (by invested amount)
        Assert(App.localGet(Gtxn[0].sender(), Bytes(LOCAL_SHARES)) <= App.globalGet(Bytes(GLOBAL_MAX_INVEST_AMOUNT))),

        # save acked prospectus
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_URL), Gtxn[1].application_args[2]),
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_HASH), Gtxn[1].application_args[3]),
        App.localPut(Gtxn[0].sender(), Bytes(LOCAL_SIGNED_PROSPECTUS_TIMESTAMP), Gtxn[1].application_args[4]),

        Approve()
    )

    handle_withdrawal = Seq(
        Assert(Global.group_size() == Int(1)),

        # only the owner can withdraw
        Assert(Gtxn[0].sender() == Global.creator_address()),

        # has to be after min target end date
        Assert(Global.latest_timestamp() > App.globalGet(Bytes(GLOBAL_TARGET_END_DATE))),

        # has to be <= available amount
        Assert(Btoi(Gtxn[0].application_args[1]) <= App.globalGet(Bytes(GLOBAL_AVAILABLE_AMOUNT))),

        # the min target was met
        # (if the target wasn't met, the project can't start and investors can reclaim their money)
        Assert(App.globalGet(Bytes(GLOBAL_RAISED)) >= App.globalGet(Bytes(GLOBAL_TARGET))),

        # decrease available amount
        App.globalPut(
            Bytes(GLOBAL_AVAILABLE_AMOUNT),
            Minus(
                App.globalGet(Bytes(GLOBAL_AVAILABLE_AMOUNT)),
                Btoi(Gtxn[0].application_args[1])
            )
        ),

        # send the funds to the withdrawer
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_amount: Btoi(Gtxn[0].application_args[1]),
            TxnField.asset_receiver: Txn.sender(),
            TxnField.xfer_asset: App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID)),
        }),
        InnerTxnBuilder.Submit(),

        Approve()
    )

    # allow the investors to get their investments back if the funding target wasn't met
    #
    # note that for reclaim, we expect the user to have unlocked the shares
    # there's no direct path from locked shares to reclaiming in teal - the app can chain these steps
    handle_reclaim = Seq(
        # app call
        is_this_noop_app_call(Gtxn[0]),

        # shares being sent back
        is_shares_transfer(Gtxn[1]),
        Assert(Gtxn[1].asset_receiver() == Global.current_application_address()),
        Assert(Gtxn[1].asset_amount() > Int(0)),
        Assert(Gtxn[1].sender() == Gtxn[0].sender()),

        # reclaiming after min target end date
        Assert(Global.latest_timestamp() > App.globalGet(Bytes(GLOBAL_TARGET_END_DATE))),

        # min target wasn't met
        Assert(
            # NOTE that raised funds currently means only investments.
            # regular payments (which could be donations) sent to the app's escrow or the customer escrow are ignored here
            # (the UI doesn't support donations (yet?), but they're of course technically possible)
            App.globalGet(Bytes(GLOBAL_RAISED)) < App.globalGet(Bytes(GLOBAL_TARGET))
        ),

        # send paid funds back
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            # TODO scratch?
            TxnField.asset_amount: Gtxn[1].asset_amount() * App.globalGet(Bytes(GLOBAL_SHARE_PRICE)),
            TxnField.asset_receiver: Gtxn[0].sender(),
            TxnField.xfer_asset: App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID)),
        }),
        InnerTxnBuilder.Submit(),

        # decrease available amount
        App.globalPut(
            Bytes(GLOBAL_AVAILABLE_AMOUNT),
            Minus(
                App.globalGet(Bytes(GLOBAL_AVAILABLE_AMOUNT)),
                Gtxn[1].asset_amount() * App.globalGet(Bytes(GLOBAL_SHARE_PRICE))
            )
        ),

        Approve()
    )

    program = Cond(
        [And(
            Gtxn[0].type_enum() == TxnType.AssetTransfer,
            Global.group_size() == Int(3)
        ), handle_invest],
        [Global.group_size() == Int(3), handle_setup_dao],
        [Gtxn[0].on_completion() == Int(4), handle_update],
        [And(
            # app call to differentiate from update, where first tx is a payment
            # TODO how do we make is_app_call usable both here and in the other (embedded in Seq) expressions?,
            Gtxn[0].type_enum() == TxnType.ApplicationCall, 
            Gtxn[0].application_id() == Int(0)
        ), handle_create],
        [Global.group_size() == Int(2), Cond(
            [Gtxn[0].type_enum() == TxnType.Payment, handle_update_data_with_image],
            [Gtxn[0].application_args[0] == Bytes("lock"), handle_lock],
            [Gtxn[0].application_args[0] == Bytes("reclaim"), handle_reclaim],
        )],
        [Gtxn[0].application_args[0] == Bytes("optin"), handle_optin],
        [Gtxn[0].application_args[0] == Bytes("unlock"), handle_unlock],
        [Gtxn[0].application_args[0] == Bytes("claim"), handle_claim],
        [Gtxn[0].application_args[0] == Bytes("drain"), handle_drain],
        [Gtxn[0].application_args[0] == Bytes("update_data"), handle_update_data_basic],
        [Gtxn[0].application_args[0] == Bytes("withdraw"), handle_withdrawal],
    )

    return compileTeal(program, Mode.Application, version=6)


def clear_program():
    return compileTeal(Int(1), Mode.Application, version=6)


def export(path, output):
    with open(path, "w") as f:
        # print(output)
        f.write(output)
        print("Wrote TEAL to: " + path)


export("teal_template/dao_app_approval.teal", approval_program())
export("teal_template/dao_app_clear.teal", clear_program())

print("Done! Wrote dao approval and clear TEAL")
