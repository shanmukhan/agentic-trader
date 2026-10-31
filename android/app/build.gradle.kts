plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.shanmukhan.agentictrader"
    compileSdk = 37
    buildToolsVersion = "36.1.0"
    defaultConfig {
        applicationId = "com.shanmukhan.agentictrader"
        minSdk = 30
        targetSdk = 37
        versionCode = 11
        versionName = "1.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    flavorDimensions += "environment"
    productFlavors {
        create("production") {
            dimension = "environment"
            buildConfigField("boolean", "DEMO", "false")
        }
        create("demo") {
            dimension = "environment"
            applicationIdSuffix = ".demo"
            versionNameSuffix = "-demo"
            buildConfigField("boolean", "DEMO", "true")
        }
    }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    if (System.getenv("AGENTIC_SIGNING_STORE") != null) {
        signingConfigs.create("privateRelease") {
            storeFile = file(System.getenv("AGENTIC_SIGNING_STORE"))
            storePassword = System.getenv("AGENTIC_SIGNING_PASSWORD")
            keyAlias = "agentic-trader"
            keyPassword = System.getenv("AGENTIC_SIGNING_PASSWORD")
            enableV1Signing = false
            enableV2Signing = true
            enableV3Signing = true
        }
        buildTypes.getByName("release").signingConfig = signingConfigs.getByName("privateRelease")
    }
    testOptions { unitTests.isReturnDefaultValues = true }
}

dependencies {
    val bom = platform("androidx.compose:compose-bom:2026.09.00")
    implementation(bom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.fragment:fragment-ktx:1.8.9")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.10.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.10.0")
    implementation("androidx.core:core-splashscreen:1.2.0")
    implementation("androidx.biometric:biometric:1.1.0")
    implementation("androidx.browser:browser:1.9.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
    implementation("com.squareup.okhttp3:okhttp:5.5.1")
    debugImplementation("androidx.compose.ui:ui-tooling")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20250517")
    androidTestImplementation(bom)
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    androidTestImplementation("androidx.test:runner:1.7.0")
    androidTestImplementation("androidx.test.ext:junit:1.3.0")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
