plugins {
    id("com.android.application") version "9.2.0"
    id("org.jetbrains.kotlin.plugin.compose") version "2.2.10"
    id("com.chaquo.python") version "17.0.0"
}

// Compatibility fix for repositories which still use the old GitHub Actions
// artifact path: app/build/outputs/apk/debug/app-debug.apk.
// The logical Gradle module remains :app, while sources live in /fullapp.
// Force build outputs into /app/build so BOTH old and new workflows find the APK.
layout.buildDirectory.set(file("../app/build"))

android {
    namespace = "com.goatsrt.manager"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.goatsrt.manager"
        minSdk = 24
        targetSdk = 37
        versionCode = 23
        versionName = "0.2.3"

        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    packaging {
        resources.excludes += setOf(
            "META-INF/AL2.0", "META-INF/LGPL2.1",
            "META-INF/LICENSE*", "META-INF/NOTICE*"
        )
    }
}

chaquopy {
    defaultConfig {
        version = "3.13"
        pyc {
            src = false
        }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.09.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.core:core-ktx:1.19.0")
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.11.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.11.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    // USB OTG seriale: CDC/ACM, FTDI, CP210x, CH34x e altri.
    implementation("com.github.mik3y:usb-serial-for-android:3.11.0")
}
