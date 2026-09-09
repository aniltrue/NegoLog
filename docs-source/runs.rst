Domains and run lifecycle
=========================

Configuration
-------------

The CLI and local web interface share validated YAML loading. Select concrete
agent/model/logger classes through the registered name or full Python import
path. Unknown fields and invalid component types produce errors. Use at least
one positive deadline: time is measured in seconds; round limits are integers.
A single configured agent requires ``self_negotiation: true``.

Before replacing an output directory, setup checks catalog rows by domain name
and loads the selected profiles. Project source/input directories and ancestor
directories cannot be output targets. Normal tournament output still replaces
the selected result directory; choose a new path to preserve a previous run.

Domain editing and generation
-----------------------------

The web editor previews changes with ``save: false`` without modifying saved
profiles or the catalog. Saving replaces the domain's catalog entry; creation
and deletion also update the catalog. Saved profiles contain the normalized
utility data used for their bid-space statistics.
Older manual profiles could retain unnormalized values while their statistics
used normalized utilities; saving now makes these agree.

The Python ``generate_domain`` and ``generate_random_domain`` helpers accept
keyword-only ``output_dir``. Successful generation replaces that domain folder;
a failure leaves the previous domain intact. Direct generator calls return
metadata and do not register an entry in the web catalog.
Domain folders and catalog workbooks are each replaced atomically, but updating
a folder and its catalog entry is not a single transaction. Ordinary catalog
write or rename failures restore the previous folder; removal failures also
restore removed folders. Process interruption between steps remains a limitation.

Random generation validates and copies its range inputs, and retains the
requested constraints. By default it raises after 1000 unsuccessful candidates;
set ``max_attempts`` to choose another positive attempt count. Infeasible
constraints raise ``ValueError`` instead of silently widening the ranges.
Issue-weight normalization now allocates integer hundredths with bounded work,
so the same seed can generate a different domain than an older version. Attempt
limits do not bound the cost of enumerating a very large domain. Undefined
normalized balance scores are represented as JSON ``null``.

Run status
----------

The local web process permits one active tournament at a time because random
streams and drawing settings are shared. Domain changes require the run to
finish. Unexpected tournament-level failures report ``Error`` and an explanation;
this is distinct from a normal session deadline without agreement (``Failed``).
Cancellation requested before startup is retained and does not replace previous
results. Cancelling an active run does not guarantee immediate interruption of
blocking native code; the existing thread-cancellation limits still apply.
