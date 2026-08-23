@echo off
echo Pushing to GitHub repository...
echo.

git add .
git commit -m "Update stock quant bot source code"
git branch -M main
git remote set-url origin https://github.com/Bosan-seo/stock-quant-bot.git
git push -u origin main

echo.
echo Done!
pause
