manta.wallet.Wallet
===================
Class for implementing a Manta Wallet

An example can be found in tests/walletdummy.py.

Basic example:

.. code-block:: python

    wallet = Wallet.factory("manta://developer.beappia.com/774747")

    try:
        envelope = await wallet.get_payment_request()
    except TimeoutError as e:
        if ONCE:
            print("Timeout exception in waiting for payment")
            sys.exit(1)
        else:
            raise e

    pr = envelope.unpack()

    logger.info("Payment request: {}".format(pr))

    # Do the transaction on block chain and send the payment

    await wallet.send_payment(transaction_hash=block, crypto_currency='NANO')

    # Listen for acks - Status can change to 'confirming', 'paid', 'invalid'

    ack = await wallet.acks.get()

.. currentmodule:: manta.wallet

.. autoclass:: Wallet
   :members:

