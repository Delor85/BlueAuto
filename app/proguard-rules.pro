# Le pont JavaScript n'expose que les méthodes annotées @JavascriptInterface.
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
