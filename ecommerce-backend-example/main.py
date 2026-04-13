
if __name__ == "__main__":
    # Run app via uvicorn for development
    import uvicorn
    uvicorn.run('app:app', host="127.0.0.1", port=8000, reload=True)