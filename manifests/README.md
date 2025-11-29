### Предварительная подготовка

Перед развёртыванием OnCall удалите все ненужные нагрузки или запущенные экземляры

```
kubectl delete --all deployments -n st-<user>
kubectl delete --all statefulsets -n st-<user>
kubectl delete --all daemonsets -n st-<user>
```

### Развёртывание СУБД MySQL

Для корректной работы OnCall требуется база данных. Будем использовать MySQL.
Разверните MySQL и связанные ресурсы:
```
export KUBE_NS=st-<ваш пользователь>

kubectl apply -f manifests/mysql/secret.yaml -n $KUBE_NS

kubectl apply -f manifests/mysql/statefulset.yaml -n $KUBE_NS

kubectl apply -f manifests/mysql/service.yaml -n $KUBE_NS
```

Проверьте, что MySQL запущен:

```
kubectl get pod -n $KUBE_NS
```

### Развёртывание приложения OnCall

Перейдём к развёртыванию OnCall.
В манифестах используются шаблоны для указания вашего неймспейса к конфигурациях и адресах для публикации.

Создайте объект конфигурации OnCall
```
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/config.yaml | kubectl apply -f - -n $KUBE_NS
```

Запустите под OnCall
```
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/deployment.yaml | kubectl apply -f - -n $KUBE_NS
```

Создайте сетевые ресурсы:

```
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/service.yaml | kubectl apply -f - -n $KUBE_NS
KUBE_NS=$KUBE_NS envsubst < manifests/oncall/ingress.yaml | kubectl apply -f - -n $KUBE_NS
```

Выполните проверку того, что все необходимые ресурсы созданы.

### Демонстрация
- После развёртывания OnCall перейдите в браузере по адресу: `http://oncall.st-<ваш пользователь>.ingress.sre-ab.ru`
- Авторизуйтесь, используя логин "root" и пароль "1234"
- Ознакомитесь с UI, создайте несколько пользователей, команду и заполните расписание дежурств на несколько дней
