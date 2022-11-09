from fastapi import FastAPI, File, Form, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse

# from utils import *

app = FastAPI()

app = FastAPI(
    title="Cartoonify API Backend",
    description="""A simple API to convert images to cartoonified images.""",
    version="0.0.1",
    docs_url=None,
    redoc_url=None,
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


templates = Jinja2Templates(directory='templates/')
app.mount('/template/static', StaticFiles(directory="static"), name="static")

# favicon_path = "templates/assets/favicon.ico"


# @app.get("/favicon.ico", include_in_schema=False)
# async def favicon():
#     return FileResponse(favicon_path)


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# @app.get("/translation")
# def home(request: Request):
#     return templates.TemplateResponse("translation.html", {"request": request})


# @app.post("/translate")
# async def home(request: Request):
#     sumary = ""
#     if request.method == "POST":
#         form = await request.form()
#         if form["message"] and form["language"]:
#             language = form["language"]
#             text = form["message"]
#             translate = get_translation(language, text)
#             sumary = " ".join(translate)

#     return templates.TemplateResponse(
#         "translation.html",
#         {"request": request, "message": text, "language": language, "sumary": sumary},
#     )
