# QR Code Feedback & FacilityBot prototype (OPS_SOP_3.4_06)

A single-page prototype for testing whether the SOP process flow works in practice.

| View | SOP step |
|---|---|
| `#scan` – QR page | Resident, family or visitor scans the QR code, picks their site (Site 1, 2 or 3), then sees two buttons only: **Feedback** (compliment / suggestion / complaint) or **Service request** (FacilityBot: fault / repair). Tapping one opens its form |
| `#ops` – Operations | Log and acknowledge (feedback must be acknowledged within 1 working day, so late cases are flagged) or receive the fault report, then assign to a department with information. Then either "Not resolved: ask the department for status" or "Resolved: close the case and inform the sender" |
| `#dept` – Department | The department acts and updates Operations |
| `#report` – Monthly report | Monthly report to the HONH: counts by type and department, acknowledgement rate, average time to close, open cases. You can copy it as text |

## Run it
Open `index.html` in a browser. Cases are saved in that browser's localStorage, and "Load example cases" fills in sample data.
`app.html` is the same page without the document wrapper. It is used for the hosted version, which shares cases across devices.

A real QR code would encode the page URL with `#scan` on the end.
