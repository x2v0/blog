# Запускаем DeepSeek Harness на Android без ПК: полный гайд

Многие думают, что запустить полноценного AI-агента (DeepSeek Harness, он же DSH) на телефоне невозможно. Мол, это серверная история, нужен Linux, Docker и гигабайты RAM.

Я тоже так думал, пока не решил собрать его в Termux. Это заняло несколько часов, мы прошли через ад зависимостей, но в итоге всё заработало. Вот пошаговая инструкция, как повторить это на своём Android.

## Что нам понадобится
* Телефон на Android (лучше 11+).
* Termux (обязательно из F-Droid! Версия из Google Play устарела и не соберёт нативные модули).
* Node.js >= 24.
* Желание возиться с компилятором C++.

## Шаг 1. Подготовка Termux
Открываем Termux и ставим базовые зависимости. Нам понадобятся компиляторы, cmake, python и NDK:

    pkg update -y && pkg upgrade -y
    pkg install -y nodejs-lts binutils make pkg-config clang python cmake patch git proot which ndk-multilib libandroid-spawn

## Шаг 2. Клонируем репозиторий адаптера
Официальный DSH написан под Linux (glibc). В Android используется bionic, поэтому «из коробки» нативные модули там не собираются. Энтузиаст Vengisk сделал слой совместимости:

    git clone https://github.com/Vengisk/deepseek-harness-termux.git
    cd deepseek-harness-termux

Внутри лежит install.sh, который сам ставит DSH и патчит его. Но не спешите его запускать — сначала нужно обойти одну ошибку.

## Шаг 3. Патчим сборщик (проблема с koffi)
koffi — это нативная библиотека для вызова C-функций. В Termux компилятор по умолчанию нацелен на старый Android API 24, где нет функции statx(). Из-за этого сборка падает.
Нужно открыть install.sh и везде, где встречается env -u CFLAGS -u CXXFLAGS -u CPPFLAGS, удалить эту конструкцию. Это заставит сборщик использовать наши флаги.
Затем экспортируем правильную архитектуру:

    export CFLAGS="-target aarch64-linux-android30"
    export CXXFLAGS="-target aarch64-linux-android30"

И запускаем установщик:

    bash install.sh

Примечание: если koffi всё равно упадёт на statx, нужно открыть node_modules/koffi/lib/native/base/base.cc в установленном DSH и заменить вызов statx(...) на syscall(__NR_statx, ...) под #if defined(__ANDROID__).

## Шаг 4. Самое сложное: сборка require-builtin
Вот тут мы застрянем, если не знать секрета. Модуль node-addon-require-builtin отвечает за загрузку встроенных модулей Node.js. В npm нет готового бинарника для Android.
Придётся собрать его из исходников:

    git clone https://github.com/deepseek-ai/dsh-node-addon-require-builtin.git
    cd dsh-node-addon-require-builtin
    npm install

Но просто запустить сборку нельзя. В файле scripts/build.ts нужно явно разрешить платформу Android, а в двух файлах platform.cc (в папках runtime_context и runtime_probe) добавить ветку #elif defined(__linux__) && defined(__aarch64__), которая перенаправит вызовы на Linux-логику.
Собираем модуль строго с нужным продуктом:

    NARB_PRODUCT=require-builtin npm run build

После сборки у вас появится файл require_builtin.node. Его нужно скопировать в установленный DSH по двум путям (чтобы загрузчик точно его нашёл):

    cp packages/require-builtin/entry/build/napi/napi-v9-android-arm64/require_builtin.node $(npm root -g)/@deepseek-ai/dsh/node_modules/node-addon-require-builtin/build/napi/napi-v9-android-arm64/
    cp packages/require-builtin/entry/build/napi/napi-v9-android-arm64/require_builtin.node $(npm root -g)/@deepseek-ai/dsh/node_modules/node-addon-require-builtin/build/nodeabi/node-v147-android-arm64/

## Шаг 5. Запуск!
Возвращаемся в домашнюю папку и запускаем:

    dsh web

Вы увидите ссылку с токеном, например:
http://127.0.0.1:3080/?token=...
Открываем её в браузере телефона (Chrome или Firefox). Появится красивый веб-интерфейс «Into the Unknown»! Выбираем рабочую папку, вводим API-ключ DeepSeek в настройках — и можно общаться с агентом.

## Итог
Мы получили полноценный DSH на телефоне. Да, пришлось повозиться с C++ и флагами компилятора, но теперь это работает локально, без всяких удалённых серверов.
В будущем, надеюсь, разработчики добавят официальную поддержку Android, и эти танцы с бубном больше не понадобятся.
