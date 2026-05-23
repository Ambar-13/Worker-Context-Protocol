# xml2rfc Conversion Guidance

The `draft-wcp-protocol-00.md` file in this directory is markdown-formatted using the kramdown-rfc dialect supported by xml2rfc and the IETF datatracker. When submission time arrives, convert to xml2rfc XML using one of the toolchain options below.

## Option 1: kramdown-rfc (recommended)

`kramdown-rfc` is the standard tool for IETF authors who prefer markdown.

```bash
gem install kramdown-rfc2629
kdrfc draft-wcp-protocol-00.md
# Produces draft-wcp-protocol-00.xml (xml2rfc v3 format)
```

Then convert XML to the final text/html/PDF outputs:

```bash
pip install xml2rfc
xml2rfc draft-wcp-protocol-00.xml --text --html --pdf
```

The kramdown-rfc dialect handles the YAML front matter, normative/informative reference sections, and most boilerplate automatically. Manual touch-ups likely needed:

- Verify the IPR statement matches the chosen IPR option (trust200902 in the front matter is standard)
- Verify the workgroup field (Independent submission for individual contribution; change if WG adopts)
- Section numbering may need adjustment if you add or reorder sections

## Option 2: pandoc to xml2rfc

If kramdown-rfc is not installed, `pandoc` can convert markdown to xml2rfc-compatible XML:

```bash
pandoc -f gfm -t xml2rfc draft-wcp-protocol-00.md -o draft-wcp-protocol-00.xml
```

Note: pandoc's xml2rfc output is less tuned than kramdown-rfc's; expect more manual cleanup.

## Option 3: direct xml2rfc authoring

For final submission, the IETF datatracker accepts xml2rfc v3 XML directly. If kramdown-rfc and pandoc don't produce the right output, the markdown is intended as a readable draft for review; convert to XML manually for the actual datatracker submission.

## Submission

Once XML is generated:

1. Validate at https://author-tools.ietf.org/idnits
2. Submit at https://datatracker.ietf.org/submit/
3. The first submission of an individual draft uses filename `draft-wcp-protocol-00.txt` (or .xml); subsequent revisions increment the `-NN` suffix.

## Sponsorship and adoption path

An individual Internet-Draft (this one) can be carried indefinitely if needed. The faster path to RFC status is working group adoption:

- Candidate WGs: RATS (Remote Attestation Procedures), ACE (Authentication and Authorization for Constrained Environments), or a new working group specifically for AI-agent and physical-worker coordination.
- Submit to a candidate WG's mailing list with the draft attached for discussion.
- WG adoption typically requires 6-12 months of mailing list discussion plus chair approval.

## Reference URLs

- IETF datatracker: https://datatracker.ietf.org/
- Author tools: https://author-tools.ietf.org/
- kramdown-rfc: https://github.com/cabo/kramdown-rfc
- xml2rfc: https://github.com/ietf-tools/xml2rfc
- IETF style guide RFC 7322: https://www.rfc-editor.org/rfc/rfc7322
