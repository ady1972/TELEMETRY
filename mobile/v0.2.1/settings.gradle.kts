pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
    // Keep plugin versions here so Gradle can resolve them before any project
    // build script is evaluated.
    plugins {
        id("com.android.application") version "9.2.0"
        id("org.jetbrains.kotlin.plugin.compose") version "2.2.10"
        id("com.chaquo.python") version "17.0.0"
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven(url = "https://jitpack.io")
    }
}

rootProject.name = "GOATSRTManagerAndroid"
include(":app")
project(":app").projectDir = file("fullapp")
