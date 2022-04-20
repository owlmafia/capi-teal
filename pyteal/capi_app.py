from pyteal import *

"""App central approval"""

tmpl_share_price = Tmpl.Int("TMPL_SHARE_PRICE")
tmpl_capi_app_id = Tmpl.Int("TMPL_CAPI_APP_ID")
tmpl_precision = Tmpl.Int("TMPL_PRECISION")
tmpl_capi_share = Tmpl.Int("TMPL_CAPI_SHARE")
tmpl_precision_square = Tmpl.Int("TMPL_PRECISION_SQUARE")
tmpl_capi_share = Tmpl.Int("TMPL_CAPI_SHARE")
tmpl_investors_share = Tmpl.Int("TMPL_INVESTORS_SHARE")
tmpl_share_supply = Tmpl.Int("TMPL_SHARE_SUPPLY")
tmpl_funds_asset_id = Tmpl.Int("TMPL_FUNDS_ASSET_ID") # TODO consider global state (like in the dao app)
tmpl_capi_asset_id = Tmpl.Int("TMPL_CAPI_ASSET_ID")

GLOBAL_RECEIVED_TOTAL = "ReceivedTotal"
LOCAL_CLAIMED_TOTAL = "ClaimedTotal"
LOCAL_CLAIMED_INIT = "ClaimedInit"
LOCAL_SHARES = "Shares"

def approval_program():
    handle_create = Seq(
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),

        Approve()
    )

    handle_setup = Seq(
        InnerTxnBuilder.Begin(),
        # optin to funds asset
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_receiver: Global.current_application_address(),
            TxnField.asset_amount: Int(0),
            TxnField.xfer_asset: tmpl_funds_asset_id,
            TxnField.fee: Int(0)
        }),
        InnerTxnBuilder.Next(),
        # optin to capi asset
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_receiver: Global.current_application_address(),
            TxnField.asset_amount: Int(0),
            TxnField.xfer_asset: tmpl_capi_asset_id,
            TxnField.fee: Int(0)
        }), 
        InnerTxnBuilder.Submit(),

        Approve()
    )

    handle_update = Seq(
        Assert(Global.group_size() == Int(1)),

        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall), 
        Assert(Gtxn[0].sender() == Global.creator_address()), 
        
        Approve()
    )

    handle_optin = Seq(
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].application_id() == Global.current_application_id()),
        Assert(Gtxn[0].on_completion() == OnComplete.OptIn),
        Approve()
    )
    
    total_entitled_dividend = Div(
        Mul(
            Div(
                Mul(App.localGet(Gtxn[0].sender(), Bytes(LOCAL_SHARES)), tmpl_precision), 
                tmpl_share_supply
            ), 
            App.globalGet(Bytes(GLOBAL_RECEIVED_TOTAL))
        ), 
        tmpl_precision
    )

    # Calculates entitled dividend based on LOCAL_SHARES and LOCAL_CLAIMED_TOTAL.
    # Expects claimer to be the gtxn 0 sender. 
    claimable_dividend = Minus(total_entitled_dividend, App.localGet(Gtxn[0].sender(), Bytes(LOCAL_CLAIMED_TOTAL)))

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
            TxnField.xfer_asset: tmpl_funds_asset_id,
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

    handle_unlock = Seq(
        Assert(Global.group_size() == Int(1)),

        # app call to opt-out
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].application_id() == Global.current_application_id()),
        Assert(Gtxn[0].on_completion() == OnComplete.CloseOut),

        # shares xfer to the investor
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_receiver: Gtxn[0].sender(),
            TxnField.asset_amount: App.localGet(Gtxn[0].sender(), Bytes(LOCAL_SHARES)),
            TxnField.xfer_asset: tmpl_capi_asset_id,
            TxnField.fee: Int(0)
        }),
        InnerTxnBuilder.Submit(),

        Approve()
    )

    handle_lock = Seq(
        Assert(Global.group_size() == Int(2)),

        # app call to update state
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].application_id() == Global.current_application_id()),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),

        # send capi assets to capi escrow
        Assert(Gtxn[1].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[1].xfer_asset() == tmpl_capi_asset_id),
        Assert(Gtxn[1].asset_receiver() == Global.current_application_address()),
        Assert(Gtxn[1].asset_amount() > Int(0)),

        # set / increment share count local state
        App.localPut( 
            Gtxn[0].sender(), 
            Bytes(LOCAL_SHARES), 
            Add(
                App.localGet(Gtxn[0].sender(), Bytes(LOCAL_SHARES)),
                Gtxn[1].asset_amount()
            )
        ),

        # set already claimed local state
        App.localPut( 
            Gtxn[0].sender(), 
            Bytes(LOCAL_CLAIMED_TOTAL), 
            # NOTE that this sets claimedTotal to the entitled amount each time that the investor buys/locks shares
            # meaning that investors may lose pending dividend by buying or locking new shares
            # TODO improve? - a non TEAL way could be to just automatically retrieve pending dividend in the same group 
            # see more notes in old repo
            claimable_dividend
            # Gtxn[1].asset_amount()
        ),

        # remember initial already claimed local state
        App.localPut( 
            Gtxn[0].sender(),
            Bytes(LOCAL_CLAIMED_INIT), 
            App.localGet(Gtxn[0].sender(), Bytes(LOCAL_CLAIMED_TOTAL))
        ),

        Approve()
    )

    handle_drain = Seq(
        Assert(Global.group_size() == Int(4)),

        # call app to verify amount and update state
        # note that we can't verify here that the correct app is being called (DAO) - probably not an issue (TODO review)
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),
        Assert(Gtxn[0].sender() == Gtxn[1].sender()), # same user is calling both apps

        # call capi app to update state
        Assert(Gtxn[1].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[1].application_id() == Global.current_application_id()),
        Assert(Gtxn[1].on_completion() == OnComplete.NoOp),

        # drain: funds xfer to DAO's escrow
        Assert(Gtxn[2].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[2].asset_amount() > Int(0)),
        Assert(Gtxn[2].xfer_asset() == tmpl_funds_asset_id),

        # pay capi fee: funds xfer to capi escrow
        Assert(Gtxn[3].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[3].xfer_asset() == tmpl_funds_asset_id),
        # no check for capi escrow receiver here as it's checked in the DAO's contract TODO review

        # update total capi fee received
        App.globalPut(
            Bytes(GLOBAL_RECEIVED_TOTAL), 
            Add(App.globalGet(Bytes(GLOBAL_RECEIVED_TOTAL)), Gtxn[3].asset_amount())
        ),

        Approve()
    )
    
    program = Cond(
        [And(Gtxn[0].application_id() == Int(0), Global.group_size() == Int(1)), handle_create],
        [Gtxn[0].application_args[0] == Bytes("optin"), handle_optin],
        [Gtxn[0].application_args[0] == Bytes("update"), handle_update],
        [Gtxn[0].application_args[0] == Bytes("claim"), handle_claim],
        [Gtxn[0].application_args[0] == Bytes("lock"), handle_lock],
        [Gtxn[0].application_args[0] == Bytes("unlock"), handle_unlock],
        [Gtxn[0].application_args[0] == Bytes("drain"), handle_drain],
        [Gtxn[0].application_args[0] == Bytes("setup"), handle_setup],
    )

    return compileTeal(program, Mode.Application, version=6)

def clear_program():
    return compileTeal(Int(1), Mode.Application, version=6)
 
def export(path, output):
   with open(path, "w") as f:
    # print(output)
    f.write(output)
    print("Wrote TEAL to: " + path)

export("teal_template/capi_app_approval.teal", approval_program())
export("teal_template/capi_app_clear.teal", clear_program())

print("Done! Wrote capi approval and clear TEAL")
