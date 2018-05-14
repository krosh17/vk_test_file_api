## vk_test_file_api
# api for magic with file

## Доступ к api только для зарегистрированных пользователей.\
Создать пользователя можно с помощью запроса

curl -X POST -H "Content-Type: application/json" -d '{"username":"user","password":"passw"}' https://vk-file-api.herokuapp.com/api/create_user

При успешном создании вы получите сообщение\
{'username': user}, 201


Для запроса подозрительных объектов из файла нужно выполнить запрос:

curl -u username:password -X POST https://vk-file-api.herokuapp.com/api/file_upload -F 'file=@"file_pass"'

## Ответ в формате:

{"users": "[{\"User_id\":\"b6b9addd48f76d3c72334243b87be538\",\"n_user_clicks\":43}, ...]",\
 "sites": "[{\"Site_id\":\"f9f32862920f6ca00c9725eade88f3d9\",\"n_sites_clck\":870}, ...]",\
 "ips": "[{\"User_IP\":\"acdd1467a82e9cb8a8177b0618a9ddc1\",\"n_clks\":43}, ...]"}

## Ограничение размера файла: 10Мб (есть ограничение на память от heroku)\
Ограничение на количество запросов: ["50 per day", "10 per hour", "5 per 5 minute"]\
(на локальной машине работает отлично как по ip, так и по логину,\
но на heroku все запросы идут через proxy и вообще непонятно работает ли =(\
не успел разобраться)


##Поднять сервис на локальной машине:

pip install -r requirements.txt\
flask db upgrade\
gunicorn --timeout 300 api:app (или python api.py)
