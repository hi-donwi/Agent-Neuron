# Third-Party Licenses

Agent-Neuron (`neuron`) is distributed under the Apache License 2.0. This file lists the
third-party Go modules compiled into the binary and their licences, as written in each
module's own licence file at the version pinned in `go.mod`.

The lab's Python dependencies (`lab/pyproject.toml`, pinned in `lab/uv.lock`) are installed
by uv from their publishers. They are not part of the binary and are not distributed with
it.

Model weights are not distributed in this repository; see [NOTICE](NOTICE).

## Direct dependencies

### github.com/spf13/cobra
- **License:** Apache License 2.0
- **Copyright:** Copyright 2013-2023 The Cobra Authors

## Indirect dependencies

### github.com/spf13/pflag
- **License:** BSD 3-Clause License
- **Copyright:** Copyright (c) 2012 Alex Ogier. All rights reserved. Copyright (c) 2012 The Go Authors. All rights reserved.

### github.com/inconshreveable/mousetrap
- **License:** Apache License 2.0
- **Copyright:** Copyright 2022 Alan Shreve (@inconshreveable)
- Linked into Windows builds only.
