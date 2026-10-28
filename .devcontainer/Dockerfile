# صورة ورشة «مركز الوعي بالمجال البحري» — تُثبَّت حزم النظام داخل الصورة نفسها،
# فلا تعتمد على تثبيت لاحق داخل الحاوية (سبب تعطّل سابق: ورشة بلا poppler وخطوط عربية).
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# أدوات خفيفة + خطوط عربية + fontconfig
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      poppler-utils fontconfig curl unzip ca-certificates \
      fonts-hosny-amiri fonts-noto-core \
 && rm -rf /var/lib/apt/lists/* \
 && fc-cache -f

# LibreOffice في طبقة منفصلة (حجمها كبير) لتسريع إعادة البناء عند تعديل ما قبلها
RUN apt-get update \
 && apt-get install -y --no-install-recommends libreoffice \
 && rm -rf /var/lib/apt/lists/* \
 && fc-cache -f

# تبعيات Chromium التي يحتاجها Playwright — لازمة لتشغيل المتصفح بلا فشل صامت
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
      libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
 && rm -rf /var/lib/apt/lists/*
