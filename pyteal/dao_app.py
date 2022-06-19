from pyteal import *

"""App central approval"""

tmpl_share_price = Tmpl.Int("TMPL_SHARE_PRICE")
tmpl_capi_escrow_address = Tmpl.Addr("TMPL_CAPI_ESCROW_ADDRESS")
# note "__" at the end so text isn't contained in TMPL_PRECISION_SQUARE
tmpl_precision = Tmpl.Int("TMPL_PRECISION__")
tmpl_capi_share = Tmpl.Int("TMPL_CAPI_SHARE")
tmpl_precision_square = Tmpl.Int("TMPL_PRECISION_SQUARE")
tmpl_investors_share = Tmpl.Int("TMPL_INVESTORS_SHARE")
tmpl_share_supply = Tmpl.Int("TMPL_SHARE_SUPPLY")

GLOBAL_RECEIVED_TOTAL = "CentralReceivedTotal"

GLOBAL_CUSTOMER_ESCROW_ADDRESS = "CustomerEscrowAddress"

GLOBAL_SHARES_ASSET_ID = "SharesAssetId"
GLOBAL_FUNDS_ASSET_ID = "FundsAssetId"

GLOBAL_LOCKED_SHARES = "LockedShares"

GLOBAL_DAO_NAME = "DaoName"
GLOBAL_DAO_DESC = "DaoDesc"
GLOBAL_SHARE_PRICE = "SharePrice"
# % of income directed to investors
GLOBAL_INVESTORS_PART = "InvestorsPart"

GLOBAL_LOGO_URL = "LogoUrl"
GLOBAL_SOCIAL_MEDIA_URL = "SocialMediaUrl"

GLOBAL_TARGET = "Target"
GLOBAL_TARGET_END_DATE = "TargetEndDate"
GLOBAL_RAISED = "Raised"

GLOBAL_VERSIONS = "Versions"

LOCAL_SHARES = "Shares"
LOCAL_CLAIMED_TOTAL = "ClaimedTotal"
LOCAL_CLAIMED_INIT = "ClaimedInit"
LOCAL_DAO_ID = "Dao"


def approval_program():
    handle_create = Seq(
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Approve()
    )

    handle_update = Seq(
        Assert(Global.group_size() == Int(1)),

        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].sender() == Global.creator_address()),

        Approve()
    )

    handle_setup_dao = Seq(
        # creator sends min balance to app address
        Assert(Gtxn[0].type_enum() == TxnType.Payment),
        Assert(Gtxn[0].receiver() == Global.current_application_address()),

        # app call
        Assert(Gtxn[1].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[1].application_id() == Global.current_application_id()),
        Assert(Gtxn[1].on_completion() == OnComplete.NoOp),
        Assert(Gtxn[1].application_args.length() == Int(12)),
        Assert(Gtxn[1].sender() == Global.creator_address()),

        # creator sends min balance to customer escrow
        Assert(Gtxn[2].type_enum() == TxnType.Payment),
        Assert(Gtxn[2].receiver() == Gtxn[1].application_args[0]),

        # customer escrow opt-ins to funds asset (lsig)
        Assert(Gtxn[3].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[3].asset_amount() == Int(0)),
        Assert(Gtxn[3].asset_receiver() == Gtxn[3].sender()),
        Assert(Gtxn[3].fee() == Int(0)), # lsig check
        Assert(Gtxn[3].asset_receiver() == Gtxn[3].sender()), # lsig check
        # todo check needed for xfer?
        Assert(Gtxn[3].rekey_to() == Global.zero_address()), # lsig check

        # creator transfers shares (to be sold to investors) to app escrow
        Assert(Gtxn[4].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[4].xfer_asset() == Btoi(Gtxn[1].application_args[1])),

        # initialize state
        App.globalPut(Bytes(GLOBAL_RECEIVED_TOTAL), Int(0)),
        App.globalPut(Bytes(GLOBAL_LOCKED_SHARES), Int(0)),

        App.globalPut(Bytes(GLOBAL_CUSTOMER_ESCROW_ADDRESS), Gtxn[1].application_args[0]),

        App.globalPut(Bytes(GLOBAL_SHARES_ASSET_ID), Btoi(Gtxn[1].application_args[1])),
        App.globalPut(Bytes(GLOBAL_FUNDS_ASSET_ID), Btoi(Gtxn[1].application_args[2])),

        App.globalPut(Bytes(GLOBAL_DAO_NAME), Gtxn[1].application_args[3]),
        App.globalPut(Bytes(GLOBAL_DAO_DESC), Gtxn[1].application_args[4]),
        App.globalPut(Bytes(GLOBAL_SHARE_PRICE), Btoi(Gtxn[1].application_args[5])),
        App.globalPut(Bytes(GLOBAL_INVESTORS_PART), Btoi(Gtxn[1].application_args[6])),

        App.globalPut(Bytes(GLOBAL_LOGO_URL), Gtxn[1].application_args[7]),
        App.globalPut(Bytes(GLOBAL_SOCIAL_MEDIA_URL), Gtxn[1].application_args[8]),

        App.globalPut(Bytes(GLOBAL_VERSIONS), Gtxn[1].application_args[9]),

        App.globalPut(Bytes(GLOBAL_TARGET), Btoi(Gtxn[1].application_args[10])),
        App.globalPut(Bytes(GLOBAL_TARGET_END_DATE), Btoi(Gtxn[1].application_args[11])),

        App.globalPut(Bytes(GLOBAL_RAISED), Int(0)),

        # checks depending on global state

        Assert(Gtxn[4].xfer_asset() == App.globalGet(Bytes(GLOBAL_SHARES_ASSET_ID))),

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

    handle_update_data = Seq(
        Assert(Global.group_size() == Int(1)),

        # app call
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].application_id() == Global.current_application_id()),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),
        Assert(Gtxn[0].application_args.length() == Int(7)),
        Assert(Gtxn[0].sender() == Global.creator_address()),

        # update data
        App.globalPut(Bytes(GLOBAL_CUSTOMER_ESCROW_ADDRESS), Gtxn[0].application_args[1]),
        App.globalPut(Bytes(GLOBAL_DAO_NAME), Gtxn[0].application_args[2]),
        App.globalPut(Bytes(GLOBAL_DAO_DESC), Gtxn[0].application_args[3]),
        # for now price is immutable, simplifies funds reclaiming
        # App.globalPut(Bytes(GLOBAL_SHARE_PRICE), Btoi(Gtxn[0].application_args[4])),
        App.globalPut(Bytes(GLOBAL_LOGO_URL), Gtxn[0].application_args[4]),
        App.globalPut(Bytes(GLOBAL_SOCIAL_MEDIA_URL), Gtxn[0].application_args[5]),
        App.globalPut(Bytes(GLOBAL_VERSIONS), Gtxn[0].application_args[6]),

        # for now shares asset, funds asset and investor's part not updatable - have to think about implications

        Approve()
    )

    handle_optin = Seq(
        Assert(Global.group_size() == Int(1)),

        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].application_id() == Global.current_application_id()),
        Assert(Gtxn[0].on_completion() == OnComplete.OptIn),
        Approve()
    )

    handle_unlock = Seq(
        Assert(Global.group_size() == Int(1)),

        # app call to opt-out
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].on_completion() == OnComplete.CloseOut),
        Assert(Gtxn[0].application_id() == Global.current_application_id()),

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
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].application_id() == Global.current_application_id()),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),

        # send dividend to caller
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_amount: claimable_dividend,
            TxnField.asset_receiver: Gtxn[0].sender(),
            TxnField.xfer_asset: App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID)),
        }),
        InnerTxnBuilder.Submit(),

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
            # TODO is this really needed?
            # Assert(Gtxn[1].asset_amount() > Int(0)), # sanity: don't allow locking 0 shares

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

    # For invest/lock. Dao id expected as first arg of the first tx
    # save the dao id in local state, so we can find daos where a user invested in (with the indexer)
    # TODO rename in CapiDao or similar - this key is used to filter for txs belonging to capi / dao id use case
    # - we don't have the app id when querying this, only the sender account and this key
    # NOTE assumes that sender of Gtxn[0] is the app caller (ownler of local state where id should be written)
    # TODO review whether really needed
    save_dao_id = App.localPut(Gtxn[0].sender(), Bytes(LOCAL_DAO_ID), Global.current_application_id())

    handle_lock = Seq(
        Assert(Global.group_size() == Int(2)),

        # app call to update state
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].application_id() == Global.current_application_id()),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),
        Assert(Gtxn[0].application_args.length() == Int(1)),

        # shares xfer to app
        Assert(Gtxn[1].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[1].xfer_asset() == App.globalGet(Bytes(GLOBAL_SHARES_ASSET_ID))),
        Assert(Gtxn[1].asset_receiver() == Global.current_application_address()),
        Assert(Gtxn[1].asset_amount() > Int(0)),

        # app caller is locking the shares
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),

        # save shares on local state
        lock_shares(Gtxn[1].asset_amount(), Gtxn[0].sender()),

        # save the dao id on local state
        save_dao_id,

        Approve()
    )

    drain_asset_balance = AssetHolding.balance(
        Gtxn[1].sender(), Gtxn[1].xfer_asset())

    handle_drain = Seq(
        Assert(Global.group_size() == Int(3)),

        # call app to verify amount and update state
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].application_id() == Global.current_application_id()),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),

        # drain: funds xfer to app escrow (lsig)
        Assert(Gtxn[1].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[1].asset_amount() > Int(0)),
        Assert(Gtxn[1].sender() == App.globalGet(Bytes(GLOBAL_CUSTOMER_ESCROW_ADDRESS))),
        Assert(Gtxn[1].xfer_asset() == App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID))),
        Assert(Gtxn[1].asset_receiver() == Global.current_application_address()),
        Assert(Gtxn[1].fee() == Int(0)), # lsig check
        Assert(Gtxn[1].asset_close_to() == Global.zero_address()), # lsig check
        # todo check needed for xfer?
        Assert(Gtxn[1].rekey_to() == Global.zero_address()), # lsig check
        # both xfers are signed by the customer escrow
        Assert(Gtxn[1].sender() == Gtxn[2].sender()),

        # pay capi fee: funds xfer to capi escrow
        Assert(Gtxn[2].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[2].xfer_asset() == App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID))),
        Assert(Gtxn[2].asset_receiver() == tmpl_capi_escrow_address),

        # check that capi fee is correct
        drain_asset_balance,  # needs to be listed like this, see: https://forum.algorand.org/t/using-global-get-ex-on-noop-call-giving-error-when-deploying-app/5314/2?u=user123
        # AssetHolding.balance(Gtxn[2].sender(), Gtxn[2].xfer_asset()),
        Assert(
            Gtxn[2].asset_amount() == Div(
                Mul(
                    Mul(drain_asset_balance.value(), tmpl_precision),
                    tmpl_capi_share
                ),
                tmpl_precision_square
            )
        ),

        # update total received
        App.globalPut(
            Bytes(GLOBAL_RECEIVED_TOTAL),
            Add(App.globalGet(Bytes(GLOBAL_RECEIVED_TOTAL)), Gtxn[1].asset_amount())
        ),

        Approve()
    )

    handle_invest = Seq(
        # Assert(Global.group_size() == Int(3)), # used as condition

        # investor opts-in to shares (needs to be before app call with inner tx sending the asset)
        # optin to shares
        Assert(Gtxn[0].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[0].xfer_asset() == App.globalGet(Bytes(GLOBAL_SHARES_ASSET_ID))),
        Assert(Gtxn[0].asset_amount() == Int(0)),
        Assert(Gtxn[0].asset_receiver() == Gtxn[0].sender()),

        # app call to initialize shares state
        Assert(Gtxn[1].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[1].application_id() == Global.current_application_id()),
        Assert(Gtxn[1].on_completion() == OnComplete.NoOp),
        Assert(Gtxn[1].application_args.length() == Int(2)),

        # investor pays for shares: funds xfer to app escrow
        Assert(Gtxn[2].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[2].asset_amount() > Int(0)),
        Assert(Gtxn[2].xfer_asset() == App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID))),
        Assert(Gtxn[2].asset_receiver() == Global.current_application_address()),

        # the investor sends all txs
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),
        Assert(Gtxn[1].sender() == Gtxn[2].sender()),

        # double-check that the share amount matches what the caller expects
        # (just in case for unexpected rounding issues)
        Assert(Div(Gtxn[2].asset_amount(), tmpl_share_price) == Btoi(Gtxn[1].application_args[1])),

        # update total raised amount
        App.globalPut(Bytes(GLOBAL_RAISED), Add(
            App.globalGet(Bytes(GLOBAL_RAISED)),
            Gtxn[2].asset_amount()
        )),

        # save shares on local state
        lock_shares(
            Div(Gtxn[2].asset_amount(), tmpl_share_price), 
            Gtxn[0].sender()
        ),

        # save the dao id on local state
        save_dao_id,

        Approve()
    )

    handle_withdrawal = Seq(
        Assert(Global.group_size() == Int(1)),

        # only the owner can withdraw
        Assert(Gtxn[0].sender() == Global.creator_address()),

        # has to be after min target end date
        Assert(Global.latest_timestamp() > App.globalGet(Bytes(GLOBAL_TARGET_END_DATE))),
        # the min target was met
        # (if the target wasn't met, the project can't start and investors can reclaim their money)
        Assert(App.globalGet(Bytes(GLOBAL_RAISED)) >= App.globalGet(Bytes(GLOBAL_TARGET))),

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

    handle_reclaim = Seq(
        Assert(Global.group_size() == Int(2)),

        # app call
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].application_id() == Global.current_application_id()),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),

        # shares being sent back
        Assert(Gtxn[1].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[1].xfer_asset() == App.globalGet(Bytes(GLOBAL_SHARES_ASSET_ID))),
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
            TxnField.asset_amount: Gtxn[1].asset_amount() * App.globalGet(Bytes(GLOBAL_SHARE_PRICE)),
            TxnField.asset_receiver: Gtxn[0].sender(),
            TxnField.xfer_asset: App.globalGet(Bytes(GLOBAL_FUNDS_ASSET_ID)),
        }),
        InnerTxnBuilder.Submit(),

        Approve()
    )

    program = Cond(
        [Global.group_size() == Int(5), handle_setup_dao],
        [Gtxn[0].on_completion() == Int(4), handle_update],
        [And(
            Gtxn[0].type_enum() == TxnType.AssetTransfer,
            Global.group_size() == Int(3)
        ), handle_invest],
        [Gtxn[0].application_id() == Int(0), handle_create],
        [Gtxn[0].application_args[0] == Bytes("optin"), handle_optin],
        [Gtxn[0].application_args[0] == Bytes("unlock"), handle_unlock],
        [Gtxn[0].application_args[0] == Bytes("claim"), handle_claim],
        [Gtxn[0].application_args[0] == Bytes("lock"), handle_lock],
        [Gtxn[0].application_args[0] == Bytes("drain"), handle_drain],
        [Gtxn[0].application_args[0] == Bytes("update_data"), handle_update_data],
        [Gtxn[0].application_args[0] == Bytes("withdraw"), handle_withdrawal],
        [Gtxn[0].application_args[0] == Bytes("reclaim"), handle_reclaim],
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
