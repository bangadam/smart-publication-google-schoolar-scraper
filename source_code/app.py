from flask import Flask, flash, render_template, redirect, url_for, request, session
from module.database import Database
from module.constants import Constants
from pprint import pprint
import requests
import bs4
from scholarly import scholarly
import json

app = Flask(__name__)
db = Database()
constants = Constants()


@app.route('/')
def index():
    return render_template('frontend/home.html')

@app.route('/lecturers')
def lecturers():
    data = db.selectLecturers()
    return render_template('frontend/lecturers/index.html', data=data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        # Create variables for easy access
        user_id = request.form['user_id']
        password = request.form['password']
        data = {
            "user_id": user_id,
            "password": password
        }
        result = db.loginCheck(data)

        if result != None:
            session['loggedin'] = True
            return render_template('frontend/home.html')
        else:
            msg = 'User ID / password salah'
            return render_template('frontend/auth/login.html', msg=msg)

    return render_template('frontend/auth/login.html', msg='')

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    return redirect('/login')

@app.route('/search-peneliti', methods=['GET'])
def searchPeneliti():
    if request.method == 'GET':
        data = request.args.get('mauthors')
        data = scrapePenelitiUser(data)
        return render_template('frontend/home.html', data=data)
    else:
        return render_template('frontend/home.html')


def scrapePenelitiUser(data):
    url = constants.SEARCH_PROFILE_API + data
    res = session.get(url)
    res = bs4.BeautifulSoup(res.content, 'html.parser')
    list_user = res.findAll('div', class_='gsc_1usr')
    data_user = []
    for item in list_user:
        name = item.find('h3', class_='gs_ai_name').find('a').text
        instansi = item.find('div', class_="gs_ai_aff").text
        email = item.find('div', class_="gs_ai_eml").text
        photo = item.find('img')['src']
        link = item.find('h3', class_='gs_ai_name').find('a')['href']
        data_user.append({
            "name": name,
            "instansi": instansi,
            "email": email,
            "photo": photo,
            "link": link
        })

    return data_user


@app.route('/detail-peneliti/<url_bio>')
def detail(url_bio):
    user_id = request.args.get('user')
    url = constants.DETAIL_USER_API + user_id
    res = session.get(url)
    res = bs4.BeautifulSoup(res.content, 'html.parser')
    data = {}

    # Data bio
    nama_peneliti = res.find('div', id='gsc_prf_in').text
    photo_peneliti = res.find('img', id='gsc_prf_pup-img')['src']
    instansi = res.find('div', class_='gsc_prf_il').text
    email = res.find('div', id='gsc_prf_ivh').text
    spesialis = res.find('div', id='gsc_prf_int').findAll('a')
    spesialis = ', '.join([str(x.text) for x in spesialis])

    if "/citations/images/avatar_scholar_128.png" in photo_peneliti:
        photo_peneliti = "https://scholar.google.com/citations/images/avatar_scholar_128.png"

    data["bio"] = {
        "nama": nama_peneliti,
        "photo": photo_peneliti,
        "instansi": instansi,
        "email": email,
        "spesialis": spesialis
    }

    # pprint(data['bio'])

    # Data jurnal
    # list_jurnal = res.findAll('tr', class_='gsc_a_tr')
    # data_jurnal = []
    # for item in list_jurnal:
    #     judul = item.find('td', class_='gsc_a_t').find('a').text
    #     author = item.find('div', class_='gs_gray').text
    #     dikutip = item.find('td', class_='gsc_a_c').text
    #     tahun = item.find('td', class_='gsc_a_y').text
    #     publish = item.select('.gs_gray+ .gs_gray')[0].text
    #     data["jurnal"].append({
    #         "judul": judul,
    #         "author": author,
    #         "dikutip": dikutip,
    #         "tahun": tahun,
    #         "publish": publish
    #     })

    # Statistik Jurnal
    search_query = scholarly.search_author(data['bio']['nama'])
    author = next(search_query).fill(['citations', 'counts', 'publications'])
    year = json.dumps(author.cites_per_year)
    year = json.loads(year)
    data_cited = []
    label_year = []

    for value, key in year.items():
        data_cited.append(key)
        # label_year.append(value)

    for item in author.cites_per_year:
        label_year.append(item)

    data['cititations'] = {
        "citedby": author.citedby,
        "label_year": label_year,
        "data_cited_year": data_cited
    }
    pprint(data)
    #
    data['publications'] = author.publications

    return render_template('frontend/detail-peneliti.html', data=data)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html')


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.run(port=8004, debug=True)
