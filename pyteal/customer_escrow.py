from pyteal import *

"""Customer escrow"""

tmpl_central_app_id = Tmpl.Int("TMPL_CENTRAL_APP_ID")
tmpl_app_escrow_address = Tmpl.Addr("TMPL_APP_ESCROW_ADDRESS")
tmpl_capi_escrow_address = Tmpl.Addr("TMPL_CAPI_ESCROW_ADDRESS")

GLOBAL_RECEIVED_TOTAL = "ReceivedTotal"
LOCAL_CLAIMED_TOTAL = "ClaimedTotal"
LOCAL_SHARES = "Shares"


def program():
    handle_setup_dao = Seq(
        # app call
        Assert(Gtxn[1].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[1].application_id() == tmpl_central_app_id),
        Assert(Gtxn[1].on_completion() == OnComplete.NoOp),

        Approve()
    )

    handle_drain = Seq(
        # app call
        Assert(Gtxn[0].type_enum() == TxnType.ApplicationCall),
        Assert(Gtxn[0].application_id() == tmpl_central_app_id),
        Assert(Gtxn[0].on_completion() == OnComplete.NoOp),

        Approve()
    )

    program = Cond(
        [Global.group_size() == Int(5), handle_setup_dao],
        [Gtxn[0].application_args[0] == Bytes("drain"), handle_drain],
    )

    program = Approve()

    return compileTeal(program, Mode.Signature, version=6)


path = 'teal_template/customer_escrow.teal'
with open(path, 'w') as f:
    output = program()
    # print(output)
    f.write(output)
    print("Done! Wrote customer escrow TEAL to: " + path)
