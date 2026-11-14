from fastapi import FastAPI

app = FastAPI(title="decode-noise placeholder")


@app.get("/health")
def health():
    return {"status": "ok", "stage": "placeholder"}


@app.get("/")
def root():
    return {"message": "decode-noise placeholder; detector not deployed yet"}
