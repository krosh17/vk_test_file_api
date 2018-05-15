# vk_test_file_api
## api for magic with file

## Доступ к api только для зарегистрированных пользователей.
Создать пользователя можно с помощью запроса

curl -X POST -H "Content-Type: application/json" -d '{"username":"user","password":"passw"}' http://18.216.135.101/api/create_user

При успешном создании вы получите сообщение\
{'username': user}, 201


Для запроса подозрительных объектов из файла нужно выполнить запрос:

curl -u username:password -X POST http://18.216.135.101/api/file_upload -F 'file=@"file_pass"'

## Ответ в формате:

{"users": "[{\"User_id\":\"b6b9addd48f76d3c72334243b87be538\",\"n_user_clicks\":43}, ...]",\
 "sites": "[{\"Site_id\":\"f9f32862920f6ca00c9725eade88f3d9\",\"n_sites_clck\":870}, ...]",\
 "ips": "[{\"User_IP\":\"acdd1467a82e9cb8a8177b0618a9ddc1\",\"n_clks\":43}, ...]"}

## Ограничение размера файла: 100Мб (слабый сервер на aws)
Ограничение на количество запросов по логину: ["20 per day", "5 per hour", "2 per 5 minute"]\
по ip: ["40 per day", "10 per hour", "5 per 5 minute"]

##Поднять сервис на локальной машине:

pip install -r requirements.txt\
flask db upgrade\
gunicorn --timeout 300 api:app (или python api.py)

##P.S.
Вместо aws можно использовать https://vk-file-api.herokuapp.com
Но там максимальный размер файла 10Мб и при превышении лимита запросов будет не кастомная ошибка.
