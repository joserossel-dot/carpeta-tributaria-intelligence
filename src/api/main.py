import gc
import io
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.core.orquestador import PipelineOrquestador
from src.db_repository import RepositorioDiccionario



repositorio: RepositorioDiccionario | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global repositorio

    repositorio = RepositorioDiccionario()
    try:
        await repositorio.inicializar()
    except RuntimeError as e:
        if "asyncpg" in str(e):
            print(f"[API] {e}")
            print("[API] Continuando sin base de datos — modo JSON fallback.")
            repositorio = RepositorioDiccionario()
            repositorio._inicializar_json()
        else:
            raise

    yield

    if repositorio:
        await repositorio.cerrar()
        repositorio = None


app = FastAPI(
    title="API de Inteligencia Financiera y Homologación",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "repositorio": repositorio is not None}


@app.post("/api/v1/analisis/procesar")
async def procesar_analisis(
    file_carpeta: UploadFile = File(...),
    file_balance: UploadFile = File(...),
    giro_empresa: str = Form(...),
):
    if repositorio is None:
        raise HTTPException(status_code=503, detail="Repositorio no disponible")

    if not file_carpeta.filename or not file_carpeta.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="file_carpeta debe ser un archivo PDF")
    if not file_balance.filename or not file_balance.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="file_balance debe ser un archivo PDF")

    buf_carpeta = None
    buf_balance = None

    try:
        carpeta_bytes = await file_carpeta.read()
        balance_bytes = await file_balance.read()
        buf_carpeta = io.BytesIO(carpeta_bytes)
        buf_balance = io.BytesIO(balance_bytes)

        orquestador = PipelineOrquestador(repositorio)
        resultado = await orquestador.procesar_analisis_completo(
            ruta_carpeta=buf_carpeta,
            ruta_balance=buf_balance,
            giro_empresa=giro_empresa,
        )

        return resultado.to_dict()

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar el análisis: {e}",
        )
    finally:
        if buf_carpeta is not None:
            buf_carpeta.close()
        if buf_balance is not None:
            buf_balance.close()
        del buf_carpeta
        del buf_balance
        gc.collect()

