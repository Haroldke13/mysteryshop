# Deploying mysteryshop to cPanel

Target: **https://mysteryshop.harold-datascience.co.ke**

No SSH on this account, so every step below is the panel or File Manager.

## 1. Create the subdomain

*Domains → Create A New Domain.*

- Domain: `mysteryshop.harold-datascience.co.ke`
- Document Root: `apps/mysteryshop/public`   ← **not** `apps/mysteryshop`

The document root is a separate folder holding only public assets. nginx serves
whatever is in it and ignores `.htaccess`, so application source must never sit
there — that is how source code ends up downloadable.

## 2. Upload

Zip this folder, upload through File Manager to `apps/mysteryshop`, extract there.

## 3. Create the Python application

*Software → Setup Python App → Create Application.*

| Field | Value |
|---|---|
| Python version | 3.11 |
| Application root | `apps/mysteryshop` |
| Application URL | `mysteryshop.harold-datascience.co.ke` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

## 4. Environment variables

Add each line of `.env.example` as a variable in that same screen. Do **not**
upload a `.env` file — this bundle deliberately ships none.

## 5. Install dependencies

Put `requirements.txt` in the *Configuration files* box and press **Run Pip
Install**.

A bare Flask virtualenv is about 41 MB, which is the floor for any app on this account.

## 6. Harden

Append `htaccess.append.txt` to the subdomain's `.htaccess`. Never replace that
file — Passenger writes its own directives into it.

## 7. Restart and check

```
https://mysteryshop.harold-datascience.co.ke/?cb=1                    -> 200
https://mysteryshop.harold-datascience.co.ke/healthz?cb=1             -> 200
https://mysteryshop.harold-datascience.co.ke/passenger_wsgi.py?cb=1   -> must 404
```

nginx caches hard, so always add a unique query string before concluding a
change did not apply. If the answer differs, you were reading a cache.

## If it 500s

Passenger writes the traceback to `~/apps/mysteryshop/stderr.log`. Read it first;
it names the failure almost every time.

## Known gap

This app does **not** start. It imports modules that were never written:

- `mysteryshop.evidence`
- `mysteryshop.exporters`
- `mysteryshop.storage`

It is bundled anyway so the gap is visible, but do not spend quota deploying it until those exist.
