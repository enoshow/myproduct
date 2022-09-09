from asyncio.windows_events import NULL
from flask import Flask, render_template, request, url_for, redirect, session, Response, make_response,send_file, send_from_directory
from datetime import timedelta 
import datetime
from werkzeug.utils import secure_filename # fileを保存するのに必要なライブラリ
import flask
from flask import send_from_directory
import os
import psycopg2
import shutil
import urllib.parse

from urllib.parse import quote

# 2007 Office system ファイル形式の MIME タイプをサーバーで登録する
# https://technet.microsoft.com/ja-jp/library/ee309278(v=office.12).aspx
XLSX_MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

app = Flask(__name__, static_folder=None)


app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024 *1024
# 最大アップロード容量 : 1GB
app.secret_key = 'abcdefghijklmn'
app.permanent_session_lifetime = timedelta(minutes=30) 
# セッション期限は30分





def get_db_connection():    # データベースの接続設定
    conn = psycopg2.connect(host='localhost',
                            database='test',
                            user='eno',
                            password='pass')
    return conn


def uidSes():   # データベースの接続設定
    if "uid" in session: 
        uid=session["uid"]
        return uid
    else:
        return None


#　-----目次--------
#　1.TOPページの処理
#　2.新規登録の処理
#　3.ログインページの処理
#　4.ログアウトの処理
#　5.マイページの処理
#　6.新規登録完了の処理
#　7.1作品の新規登録の処理
#　7.2作品の新規登録の処理2
#　8.作品の編集・登録完了
#　9.検索処理
# 10.成果物の詳細ページ
# 11.マイページ編集ページ
# 12.1成果物編集ページ
# 12.2成果物編集ページ
# 13.成果物downloadページ
# 14.作成者の詳細ページ
# 14.成果物の削除ページ



# 1.TOPページの処理------------------------------------------------------------------------------1
@app.route('/') 
def top():

    uid=uidSes()
    # ログインされていれば、uidを取得

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT p_name,rf_date,user_id,p_id FROM product_data ORDER BY rf_date DESC LIMIT 10;') 
    c_products = cur.fetchall() 
    #　成果物データの「成果物名、更新日時、名前（ユーザデータ）」をrf_date（更新日時）の降順で、10件取得
    cur.close()
    conn.close()
    return render_template('top.html', uid=uid,c_products=c_products)
    # topページに取得した値を渡す



# 2.新規登録の処理---------------------------------------------------------------------------------------2
@app.route('/add_member/', methods=('GET', 'POST')) 
def newmember():

    uid=uidSes()
    # ログインされていれば、uidを取得

    if request.method == 'POST':
        id=request.form['id']
        name = request.form['name']
        born = request.form['born']
        email = request.form['email']
        op_email = request.form['op_email']
        passWord = request.form['passWord']
        check_pass = request.form['check_pass']

        session.permanent = True
        session["fid"] = id     # IdをセッションIdとして格納

        if passWord != check_pass:      #　パスワード(passWord)が確認用(check_pass)と一致しなかった時の処理
            messege='パスワードが”確認用”と一致しませんでした。'
            return render_template('newmember.html',uid=uid,messege=messege)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM user_data WHERE user_id ='{id}'")
        result = cur.fetchall()     # IDがテーブルに存在するかチェックする処理

        if result!=[]:      ##　IDがすでに存在した時の処理 ##
            messege2='このIDは使用できません。'
            return render_template('newmember.html',uid=uid,messege2=messege2,
            id=id,name=name,born=born,email=email,op_email=op_email,passWord=passWord,check_pass=check_pass)

        cur.execute("INSERT INTO user_data (name, email, p_email, birth_day, password,user_id) VALUES "
                    f"('{name}','{email}', '{op_email}', '{born}', '{passWord}','{id}')")
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('newmember_check'))
        
    return render_template('newmember.html',uid=uid)



# 3.ログインページの処理-------------------------------------------------------------------------------------------3
@app.route('/login/', methods=('GET', 'POST'))
def login():

    uid=uidSes()
    # ログインされていれば、uidを取得

    if request.method == 'POST':
        uid = request.form['id']
        passWord = request.form['password']
        #IDとパスワードの受け取り

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT id FROM user_data WHERE user_id='{uid}' AND password ='{passWord}' ")
        result = cur.fetchall() 
        conn.commit()
        cur.close()
        conn.close()    

        if result == []:
            messege='IDまたはパスワードが間違っています。'
            return render_template('login.html',uid=uid,messege=messege)
            # IDかパスワードがあっていなかったときの処理
        
        session.permanent = True
        session["uid"] = uid
        ID=result[0]
        # print(ID,type(ID)) # result[0]中身と型の確認
        d_id=ID[0]
        session["id"]=d_id
        # print(d_id,type(d_id)) # ID[0]の中身と型の確認
        # idをセッションuidに格納

        return redirect(url_for('mypage'))
        
    return render_template('login.html',uid=uid)



# 4.ログアウトの処理-------------------------------------------------------------------------------------------4
@app.route('/logout/')
def logout():

    if "uid" in session: #sessionにユーザー情報があったとき
        session.pop("uid", None)
        session.pop("id", None)
        return render_template('logout.html')

    return redirect(url_for('login')) 
    #sessionにユーザー情報がなかったときはloginページに遷移



# 5.マイページの処理-------------------------------------------------------------------------------------------5
@app.route('/mypage/', methods=('GET', 'POST'))
def mypage():

    if "uid" in session: #sessionにユーザー情報があったとき
        uid=session["uid"]
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT p_name,rf_date,user_id, p_id FROM product_data"
        f" WHERE user_id ='{uid}' order by rf_date;") 
        c_products = cur.fetchall() 
        #　成果物データの「成果物名、更新日時、ID（本当は名前にしたい）」をrf_date（更新日時）の昇順で、10件取得
        return render_template('mypage.html',c_products=c_products,uid=uid)

    return redirect(url_for('login')) #sessionにユーザー情報がなかったときはloginページに遷移



# 6.新規登録完了の処理-------------------------------------------------------------------------------------------6
@app.route('/add_success/', methods=('GET', 'POST'))
def newmember_check():

    uid=uidSes()
    # ログインされていれば、uidを取得

    if "fid" in session: 
        fid=session["fid"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT user_id,id,name,email,p_email,birth_day,password FROM user_data WHERE user_id='{fid}';") 
        u_data = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('newmember-check.html',u_data=u_data,uid=uid)

    return redirect(url_for('login'))



# 7.1作品の新規登録の処理---------------------------------------------------------------------------------------7.1
@app.route('/my_prd/', methods=('GET','POST')) 
def my_prd():

    uid=uidSes()
    # ログインされていれば、uidを取得

    if "uid" in session:            
        if request.method == 'POST':

            name = request.form['p_name']
            text = request.form['text']
            code = request.form['code']

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM product_data WHERE p_name='{name}' AND user_id='{uid}'")
            result = cur.fetchall()
            conn.commit()
            cur.close()
            conn.close()

            if result != []:
                messege='すでに登録されている名前です。'
                return render_template('my-prd.html',uid=uid,messege=messege,name=name,text=text,code=code)
                # 成果物名が被ったときの処理

            session["name"]=name
            session["text"]=text
            session["code"]=code
            # 次のページまで維持するため、入力内容を一時保存

            return redirect(url_for('my_prd2'))

        return render_template('my-prd.html',uid=uid)
        
    return redirect(url_for('login'))



# 7.2作品の新規登録の処理2---------------------------------------------------------------------------------------7.2
@app.route('/my_prd2/', methods=('GET','POST')) 
def my_prd2():

    uid=uidSes()
    # ログインされていれば、uidを取得

    if "uid" in session: 
        id=session["id"]
        name = session["name"]
        text = session["text"]
        code = session["code"]
        filenames=''
        if request.method == 'POST':
            
            time=str(datetime.datetime.now())   # 更新日時用の時間を取得

            if 'file' not in flask.request.files:
                messege='ファイルが未指定です'
                return render_template('my-prd2.html',uid=uid,messege=messege)
            # ファイルがなかった場合の処理
            files = request.files.getlist('file')   # ファイルを変数に格納

            upath=f"./uploads/{uid}"
            npath=upath+f"/{name}"
            if not os.path.exists(upath):
                os.mkdir(upath)
            os.mkdir(npath)  # ユーザ、成果物ディレクトリの作成。

            c=0 # シーケンス処理用の値
            for file in files:
                if file.filename == '':   # ファイル名がなかった時の処理
                    messege='いずれかのファイルの名前がありません'
                    return render_template('my-prd2.html',uid=uid,messege=messege)

                filename = file.filename
                # ファイル名の取り出し
                if c==0:
                    filenames+=filename
                else:
                    filenames+=','+filename
                # filenamesにファイルの名前を追加
                file.save(os.path.join(npath, str(c))) # ファイル名はシーケンスで保存（日本語バグを防ぐため）
                c+=1

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO product_data (p_name, p_detail, code, u_id,rf_date,user_id,f_path,file_name) VALUES "
            f"('{name}','{text}','{code}',{id},'{time}','{uid}','{npath}','{filenames}')")
            conn.commit()
            cur.close()
            conn.close()
            
            session.pop(name,None)
            session.pop(text,None)
            session.pop(code,None)
            # 一時保存していたセッションを削除
            return redirect(url_for('prd_add_success'))

        return render_template('my-prd2.html',uid=uid,name=name,text=text,code=code)

    return redirect(url_for('login'))



# 8.作品の編集・登録完了-------------------------------------------------------------------------------------------.8
@app.route('/prd_add_success/', methods=('GET', 'POST'))
def prd_add_success():

    if "uid" in session: 
        uid=session["uid"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT user_id,id,name,email,p_email,birth_day,password FROM user_data WHERE user_id='{id}';") 
        u_data = cur.fetchall() 
        cur.close()
        conn.close()
        return render_template('my-prd-ed-notice.html',u_data=u_data,uid=uid)

    return redirect(url_for('login'))



# 9.検索処理------------------------------------------------------------------------------9
@app.route('/search/', methods=('GET', 'POST')) 
def search():

    uid=uidSes()
    # ログインされていれば、uidを取得
    word=None
    if request.method == 'POST':
        word = request.form["search"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT p_name,rf_date,user_id,p_id FROM product_data WHERE p_name LIKE '%{word}%';") 
        result = cur.fetchall() 
        # 成果物名の中間一致で、成果物名と更新日時、ID」を検索
        cur.close()
        conn.close()
        return render_template('search.html', uid=uid,word=word,result=result)
    return render_template('search.html',word=word,uid=uid)



# 10.成果物の詳細ページ------------------------------------------------------------------------------10
@app.route('/prd/<string:pid>/') 
def prd(pid):

    uid=uidSes()
    # ログインされていれば、uidを取得

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT user_id,p_name,p_detail,code,rf_date,p_id FROM product_data WHERE p_id={pid};") 
    result = cur.fetchall() 
    # 成果物名の中間一致で、成果物名と更新日時、IDを検索
    cur.execute(f"SELECT file_name FROM product_data WHERE p_id={pid};") 
    result2 = cur.fetchall()
    cur.close()
    conn.close()

    #　DBから得た結果を','で区切られた文字列にし、split()でただのlistにする　#
    ################################ つまり、無駄な文字（(、]、"など）を省く処理##
    files=result2[0]
    l_files=list(files)
    c=0
    files=''
    for n in l_files:
        if c==0:
            files=n
        else:
            files+=','+n
        c+=1
    s_fname=files.split(',')
    #################################

    return render_template('prd-page.html', uid=uid,result=result,s_fname=s_fname)



# 11.マイページ編集ページ-------------------------------------------------------------------------------------------11
@app.route('/mypage_ed/', methods=('GET', 'POST'))
def mypage_ed():

    uid=uidSes()
    # ログインされていれば、uidを取得

    if "uid" in session: 
        conn = get_db_connection()
        cur = conn.cursor()

        ##### ここから、再登録ボタンを押された時の処理 #######################
        if request.method == 'POST':
            id=request.form['id']
            name = request.form['name']
            born = request.form['born']
            email = request.form['email']
            op_email = request.form['op_email']
            passWord = request.form['passWord']
            text = request.form['text']

            u_data=[] # u_dataの初期化

            cur.execute(f"SELECT user_id,name,email,p_email,birth_day,password,ad_detail FROM user_data WHERE user_id='{uid}';") 
            u_data = cur.fetchall()

            # IDを変更したうえで、変更したIDがテーブルに存在するかチェック
            if not id==uid:
                cur.execute(f"SELECT * FROM user_data WHERE user_id ='{id}'")
                result = cur.fetchall() 
                if result!=[]:
                    messege=f"ID'{id}'は使用できません"
                    return render_template('newmember.html',uid=uid,messege=messege,u_data=u_data,
                    id=id,name=name,born=born,email=email,op_email=op_email,passWord=passWord,text=text)
                #　IDがすでに存在した時の処理
            cur.execute(f"UPDATE user_data SET name='{name}', email='{email}', "
                        f"p_email='{op_email}', birth_day= '{born}', password='{passWord}', user_id='{id}', ad_detail='{text}' "
                        f"WHERE user_id='{uid}'")
            conn.commit()
            cur.close()
            conn.close()
            return render_template('mypage-ed-notice.html',uid=uid)
        ####　ここまで再登録ボタン押された時処理 #######################


        uid=session["uid"]
        cur.execute(f"SELECT user_id,name,email,p_email,birth_day,password,ad_detail FROM user_data WHERE user_id='{uid}';") 
        u_data = cur.fetchall()
        cur.close()
        conn.close()
        return render_template('mypage-edit.html',u_data=u_data,uid=uid)
    
    else:
        return redirect(url_for('login'))



# 12.1成果物編集ページ-------------------------------------------------------------------------------------------12.1
@app.route('/prd_ed/<string:pid>', methods=('GET', 'POST'))
def prd_ed(pid):

    uid=uidSes()
    # ログインされていれば、uidを取得

    if "uid" in session: 
        conn = get_db_connection()
        cur = conn.cursor()
        #　DBの接続
        cur.execute(f"SELECT * FROM product_data WHERE p_id='{pid}';") 
        p_data = cur.fetchall()
        conn.commit()
        #　現在登録されているデータの取得

        ##### ここから、次へボタンを押された時の処理 #######################
        if request.method == 'POST':
            name = request.form['p_name']
            text = request.form['text']
            code = request.form['code']

            np_data=[] # p_data（現在まで登録されていたデータを取得していたリスト）の初期化

            cur.execute(f"SELECT * FROM product_data WHERE p_id={pid} AND p_name='{name}';") 
            result = cur.fetchall()

            if result != []:#　元のデータと作品名が一致しているか確認

                cur.execute(f"SELECT * FROM product_data WHERE user_id='{uid}' AND p_name='{name}';") 
                result = cur.fetchall()

                if result == []:#　同じユーザが元のデータ以外と作品名が一致しているか確認
                    messege='既に登録されている作品名であるため、登録できません。'
                    return render_template('my-prd-edit.html',uid=uid,messege=messege,name=name,text=text,code=code)
            # IDかパスワードがあっていなかったときの処理
      
            session["pid"]=pid
            session["name"]=name
            session["text"]=text
            session["code"]=code
            cur.close()
            conn.close()
            #　pidを次のページに渡すため、セッションに格納（めんどくさかった）
            return redirect(url_for('prd_ed2',pid=pid,name=name,text=text,code=code))
            
        ####　ここまで次へボタン押された時処理 #######################

        return render_template('my-prd-edit.html',p_data=p_data,uid=uid)
        #　現在登録されているデータをページ送る

    return redirect(url_for('login'))



# 12.2成果物編集ページ 2 -------------------------------------------------------------------------------------------12.2
@app.route('/prd_ed2/', methods=('GET', 'POST'))
def prd_ed2():

    uid=uidSes()
    # ログインされていれば、uidを取得

    if "uid" in session: 
        conn = get_db_connection()
        cur = conn.cursor()
        pid=session["pid"]
        name=session["name"]
        text=session["text"]
        code=session["code"]
        #　セッションから値を受け取り、不要なのでセッション削除

        ##### ここから、再登録ボタンを押された時の処理 ###################################################################
        if request.method == 'POST':
            
            files = request.files.getlist('file')
            # ファイルを変数に格納

            if 'file' not in flask.request.files:
                messege='ファイルが未指定です'
                return render_template('my-prd-edit2.html',uid=uid,messege=messege,name=name,text=text,code=code)
                # ファイルがなかった場合の処理
            
            cur.execute(f"SELECT f_path FROM product_data WHERE p_id={pid};") 
            result = cur.fetchall()
            fpath=result[0]
            print(0,result,type(result),'\n',1,fpath,type(fpath))# 型の確認
            fpath=list(fpath)
            oldpath = f"{fpath[0]}"
            # DBに格納されていたパスを取得し、使える型に変換

            shutil.rmtree(f"{oldpath}")
            #　ディレクトリごとファイルを削除

            npath=f"./uploads/{uid}/{name}"
            os.mkdir(npath)
            # 成果物ディレクトリの作成。

            c=0
            filenames=''
            for file in files:
                if file.filename == '':     # ファイル名がなかった時の処理
                    messege='いずれかのファイルの名前がありません'
                    return render_template('my-prd.html',uid=uid,messege=messege,name=name,text=text,code=code)

                filename=file.filename
                if c==0:
                    filenames+=filename
                else:
                    filenames+=','+filename     # filenamesにファイルの名前を追加     
                file.save(os.path.join(npath, str(c)))    # ファイルの保存
                c+=1
            
            time=str(datetime.datetime.now())   # 更新日時用の時間を取得

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(f"UPDATE product_data SET p_name='{name}', p_detail='{text}', code='{code}', "
            f"rf_date='{time}',f_path='{npath}',file_name='{filenames}' WHERE p_id={pid}")
            conn.commit() # データベースのデータを更新
            cur.close()
            conn.close()

            #　セッションいらないので削除
            session.pop("pid",None)
            session.pop("name",None)
            session.pop("text",None)
            session.pop("code",None)
            return redirect(url_for('prd_add_success'))

        ####　ここまで再登録ボタン押された時処理 ###############################################################################

        cur.execute(f"SELECT user_id,p_name,p_detail,code,rf_date,p_id FROM product_data WHERE p_id={pid};") 
        result = cur.fetchall() # 成果物のデータを取得

        cur.execute(f"SELECT file_name FROM product_data WHERE p_id={pid};") 
        result2 = cur.fetchall() # ファイルの名前を取得

        #　DBから得た結果を','で区切られた文字列にし、split()でただのlistにする　#
        # つまり、無駄な文字（(、]、"など）を省く処理
        # これらの処理の結果、正しいファイルパスが得られるようになり、ファイルのダウンロードページに遷移することが可能に。
        files=result2[0]
        l_files=list(files)
        c=0
        files=''
        for n in l_files:
            if c==0:
                files=n
            else:
                files+=','+n
            c+=1
        s_fname=files.split(',')

        cur.close()
        conn.close()
        return render_template('my-prd-edit2.html',result=result,uid=uid,s_fname=s_fname,name=name,text=text,code=code)

    return redirect(url_for('login'))



# 13.成果物downloadページ-------------------------------------------------------------------------------------------13
@app.route('/download/<string:f_data>', methods=('GET', 'POST'))
def download(f_data):

    fd=f_data.split(',') # fd= ['23', '工程表.xlsx']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT f_path,file_name FROM product_data WHERE p_id={fd[0]};") 
    result = cur.fetchall()
    results=result[0]
    results=list(results)
    filepath=results[0] # fpath= ./uploads/yuuu/日本語変換
    filenames=results[1]      # list(tuple) >>> tuple
    fnsp=filenames.split(',')

    c=fnsp.index(fd[1]) # クリックした文字が、DBのファイル名一覧の何番目にあるか探す
    print(c,type(c))
    fpath=filepath+'/'+str(c)

    downloadFileName=fnsp[c]   # 保存時のファイル名を一意の数字にするので、
                                        #その数字をもとに名前のリストから名前を引き出す
    print(1,downloadFileName,type(downloadFileName))
    print(2,filepath,type(filepath))
    print(3,fd,type(fd))

    path2=filepath+'/'+downloadFileName

    if os.path.isfile(fpath):
        os.rename(fpath, path2)
        
    return send_file(path2, as_attachment = True)
        
    # 日本語でファイルをダウンロードする別の方法
    # しかし、パスの設定や仕組みがよくわからず、形だけ残しておく
    #response = make_response()
    #wb = open( downloadFileName, "r" )
    #response.data = wb.read()
    #wb.close()
    #response.headers['Content-Disposition'] = "attachment; filename={}".format( urllib.parse.quote( downloadFileName ))
    #response.mimetype = 'text/csv'
    #os.remove(downloadFileName)
    #return response
        


# 14.作成者の詳細ページ------------------------------------------------------------------------------14
@app.route('/editer/<string:id>/') 
def editer(id):

    uid=uidSes()
    # ログインされていれば、uidを取得

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT p_name,rf_date,user_id, p_id FROM product_data"
                f" WHERE user_id ='{id}' order by rf_date;") 
    c_products = cur.fetchall() 
    # 作品のデータ

    cur.execute(f"SELECT name,p_email,ad_detail,user_id FROM user_data WHERE user_id='{id}';") 
    u_data = cur.fetchall() 
    # 作成者データ
    cur.close()
    conn.close()

    return render_template('editer-page.html', uid=uid,u_data=u_data,c_products=c_products)



# 15.成果物deleteページ-------------------------------------------------------------------------------------------15
@app.route('/delete/<string:pid>', methods=('GET', 'POST'))
def delete(pid):

    pid=str(pid)
    uid=uidSes()
    # ログインされていれば、uidを取得

    if "uid" in session:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT p_name,p_detail,code,rf_date,file_name,p_id,f_path FROM product_data WHERE p_id={pid};") 
        p_data = cur.fetchall()
        cur.execute(f"SELECT file_name FROM product_data WHERE p_id={pid};") 
        result2 = cur.fetchall()

        files=result2[0]
        l_files=list(files)
        c=0
        files=''
        for n in l_files:
            if c==0:
                files=n
            else:
                files+=','+n
            c+=1
        s_fname=files.split(',')

        if request.method == 'POST':
            cur.execute(f"DELETE FROM product_data WHERE p_id={pid};")
            conn.commit()
            p_datas=p_data[0]
            p_datas=list(p_datas)
            fpath=p_datas[6]
            print(fpath,type(fpath))#中身チェック
            shutil.rmtree(f"{fpath}")
            #　ディレクトリごとファイルを削除
            mess='削除完了'
            messege='削除が完了しました。'
            return render_template('notice.html',mess=mess,messege=messege,uid=uid)

        return render_template('delete.html',u_data=p_data,s_fname=s_fname,uid=uid)

    else:
        return redirect(url_for('login'))