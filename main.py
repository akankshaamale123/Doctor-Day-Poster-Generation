import uvicorn

if __name__ == '__main__':
    print("🏥 Doctor Poster API Starting...")
    print("📚 API Docs: http://localhost:5000/docs")
    print("📖 Redoc: http://localhost:5000/redoc")
    uvicorn.run(
        "route:app",
        host="0.0.0.0",
        port=5000,
        reload=True  # Set to False in production
    )