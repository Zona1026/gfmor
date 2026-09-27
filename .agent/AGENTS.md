更改程式碼後，若驗證完畢，請關閉所有驗證用的服務，使用者要測試會自己開uvicorn main:app --reload、npm run dev，若沒關閉會造成不必要的port占用以及使用者電腦卡頓

使用worktree時，可以放心將設定檔一同複製到worktree，本機的設定檔全部都指向本機資料庫，不會汙染線上的資料庫

