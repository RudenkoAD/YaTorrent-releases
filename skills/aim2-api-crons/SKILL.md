---
name: aim2-api-crons
description: Создавать и редактировать регулярные эксперименты AIM2, проверять расписание, включать и выключать кроны, запускать вручную и читать историю через API.
---

# Кроны AIM2

Прочитай [подключение](../aim2-api/SKILL.md) и формат host_configs в
[экспериментах](../aim2-api-experiments/SKILL.md).

Крон хранит basket_id и собственные host_configs; это не ссылка на изменяемый
experiment_id. Для каждого запуска фиксируются cron_revision, конфиги и ревизия
корзины, а затем создаётся обычный experiment instance.

## Расписание и создание

Из запроса должны быть понятны корзина, варианты хостов, время, timezone и
нужно ли включать расписание сейчас. Используй часовой пояс пользователя;
если он неизвестен, явно укажи допущение или уточни его. Серверный default —
Europe/Moscow. Сначала вызови `POST /crons/preview`:

```json
{"expression":"0 9 * * mon-fri","timezone":"Europe/Moscow"}
```

Ответ `upcoming_runs` содержит пять UTC timestamp. Переведи их в выбранный
часовой пояс и проверь, что получились ожидаемые дни/часы.

`POST /crons` принимает:

```json
{
  "name": "Будничный сбор",
  "basket_id": 123,
  "host_configs": [{"host": {}, "meta": {"name": "Выбранный вариант", "batch_size": 50}}],
  "expression": "0 9 * * mon-fri",
  "timezone": "Europe/Moscow",
  "enabled": false,
  "allow_concurrent": false
}
```

Пустой host здесь — место для выбранного рабочего конфига, не готовое задание.
Задавай enabled и allow_concurrent явно. Для поручения «запускай каждый день»
включение входит в задачу; для подготовки без ясного разрешения на регулярные
запуски используй enabled:false. При allow_concurrent:false занятый queued/running
крон даёт skipped следующей попытке, а не откладывает её. Серверный default — true.

После записи `GET /crons/{id}`: проверь revision, basket_id, конфиг, enabled,
allow_concurrent, next_run_at и upcoming_runs. У create нет идемпотентного ключа;
после потерянного ответа проверь кандидатов через список и подробный GET, прежде
чем повторять POST.

## Изменение и история

| Действие | Запрос |
| --- | --- |
| Найти крон | `GET /crons?limit=100&offset=0&q=<encoded-search>` |
| Прочитать полный конфиг | `GET /crons/{id}` |
| Изменить | `PUT /crons/{id}` с полным объектом и expected_revision |
| Включить/выключить | `PATCH /crons/{id}/enabled` с enabled и expected_revision |
| Ручной запуск | `POST /crons/{id}/instantiate` с request_id UUID |
| История | `GET /crons/{id}/runs?limit=100&offset=0` |
| Состояние запуска | `GET /crons/{id}/runs/{run_id}` |
| Снимок запуска | `GET /crons/{id}/runs/{run_id}/config` |

Список может возвращать host_configs:null для экономии трафика; это не пустой
конфиг. Для PUT используй свежий подробный GET и `expected_revision`; при 409
разбери чужое изменение. Выключение приостанавливает будущий приём по расписанию,
но не отменяет принятые запуски. Ручной instantiate работает даже у disabled-крона
и не сдвигает расписание. Удаления кронов через API нет.

Перед instantiate сохрани новый request_id на диск. После неизвестного исхода
повторяй тот же UUID. Runtime проверяй через `/experiments-runtime`: enabled-крон
и работающий сбор — разные состояния. Не включай backend/broker ради проверки.
Для выходных файлов используй [результаты](../aim2-api-results/SKILL.md): CronRun
содержит instance; его subexperiments содержат serpset_id.

Поддерживается обычное расписание из пяти полей, без секунд, @daily и Quartz.
Если day-of-month и day-of-week оба ограничены без звёздочки, действует OR;
проверяй preview, особенно при шагах. Пропущенные при простое сервера слоты
не догоняются. В DST отсутствующая минута пропускается, повторная выполняется
один раз. Отчёт содержит ID, ревизию, enabled, timezone и ближайшие даты.
