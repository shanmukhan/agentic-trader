package com.shanmukhan.agentictrader

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.selection.toggleable
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONArray
import org.json.JSONObject

val Ink = Color(0xFF16313B)
val Teal = Color(0xFF167C72)
val CanvasColor = Color(0xFFF4F7F9)
val Line = Color(0xFFDDE7EC)
val LocalFormEnabled = staticCompositionLocalOf { true }

@Composable fun TraderTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = lightColorScheme(primary = Teal, onPrimary = Color.White,
        primaryContainer = Color(0xFFE2F3EE), secondary = Color(0xFF51737B),
        secondaryContainer = Color(0xFFE2F3EE), onSecondaryContainer = Teal,
        background = CanvasColor, surface = Color.White, surfaceContainer = CanvasColor,
        onBackground = Ink, onSurface = Ink, onSurfaceVariant = Color(0xFF577079),
        outline = Color(0xFFB9CDD4), error = Color(0xFFB42318)),
        shapes = Shapes(medium = RoundedCornerShape(18.dp), large = RoundedCornerShape(24.dp)), content = content)
}

@Composable fun Section(title: String, caption: String = "", content: @Composable ColumnScope.() -> Unit) {
    Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White), border = BorderStroke(1.dp, Line)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            if (title.isNotBlank()) Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            if (caption.isNotBlank()) Text(caption, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            content()
        }
    }
}

@Composable fun Hint(text: String, error: Boolean = false, success: Boolean = false) {
    if (text.isBlank()) return
    val color = if (error) Color(0xFF8A291F) else if (success) Color(0xFF166344) else Color(0xFF715016)
    val background = if (error) Color(0xFFFFEFED) else if (success) Color(0xFFE9F8EF) else Color(0xFFFFF8E9)
    Surface(color = background, shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth()
        .semantics { liveRegion = LiveRegionMode.Polite }) {
        Row(Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(if (error) Icons.Outlined.ErrorOutline else if (success) Icons.Outlined.CheckCircle else Icons.Outlined.Info,
                contentDescription = null, tint = color, modifier = Modifier.size(22.dp))
            Text(text, color = color, style = MaterialTheme.typography.bodyMedium, lineHeight = 21.sp)
        }
    }
}

@Composable fun Action(text: String, enabled: Boolean = true, secondary: Boolean = false,
                       destructive: Boolean = false, onClick: () -> Unit) {
    val modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)
    if (secondary) OutlinedButton(onClick, modifier, enabled = enabled, shape = RoundedCornerShape(14.dp)) { Text(text) }
    else Button(onClick, modifier, enabled = enabled, shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(containerColor = if (destructive) MaterialTheme.colorScheme.error else Teal)) {
        Text(text, fontWeight = FontWeight.SemiBold)
    }
}

@Composable fun Field(label: String, value: String, onValue: (String) -> Unit, help: String = "",
                      numeric: Boolean = false, secret: Boolean = false, multiline: Boolean = false) {
    OutlinedTextField(value, onValue, label = { Text(label) }, modifier = Modifier.fillMaxWidth(),
        enabled = LocalFormEnabled.current,
        shape = RoundedCornerShape(14.dp), minLines = if (multiline) 3 else 1, maxLines = if (multiline) 12 else 1,
        singleLine = !multiline, keyboardOptions = KeyboardOptions(keyboardType = if (secret) KeyboardType.Password else if (numeric) KeyboardType.Decimal else KeyboardType.Text),
        visualTransformation = if (secret) PasswordVisualTransformation() else VisualTransformation.None,
        supportingText = if (help.isNotBlank()) ({ Text(help) }) else null)
}

@Composable fun Choice(label: String, value: String, options: List<Pair<String, String>>, onValue: (String) -> Unit,
                      placeholder: String = "Choose explicitly", enabled: Boolean = true) {
    var expanded by remember { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, style = MaterialTheme.typography.labelLarge)
        Box {
            OutlinedButton({ expanded = true }, enabled = enabled && LocalFormEnabled.current, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp), shape = RoundedCornerShape(14.dp)) {
                Text(options.find { it.first == value }?.second ?: placeholder, Modifier.weight(1f))
                Icon(Icons.Outlined.ExpandMore, null)
            }
            DropdownMenu(expanded, { expanded = false }, Modifier.heightIn(max = 360.dp)) {
                options.forEach { (key, text) -> DropdownMenuItem(text = { Text(text) }, onClick = { expanded = false; onValue(key) }) }
            }
        }
    }
}

@Composable fun Acknowledge(text: String, checked: Boolean, changed: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
        .toggleable(checked, enabled = LocalFormEnabled.current, role = Role.Checkbox, onValueChange = changed).semantics(mergeDescendants = true) {}) {
        Checkbox(checked, null)
        Text(text, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable fun Metric(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier.padding(vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelMedium)
        Text(value, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
    }
}

@Composable fun EmptyState(title: String, detail: String) {
    Column(Modifier.fillMaxWidth().padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Icon(Icons.Outlined.Inbox, null, Modifier.size(36.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(title, fontWeight = FontWeight.SemiBold)
        Text(detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable fun DetailCard(title: String, value: JSONObject, open: Boolean = false, external: (String) -> Unit = {}) {
    var expanded by remember(title, value.keys().asSequence().toList()) { mutableStateOf(open) }
    Section("") {
        TextButton({ expanded = !expanded }, modifier = Modifier.fillMaxWidth()) {
            Text(title, Modifier.weight(1f), color = Ink, fontWeight = FontWeight.SemiBold)
            Icon(if (expanded) Icons.Outlined.ExpandLess else Icons.Outlined.ExpandMore, null)
        }
        if (expanded) DetailTree(value, external = external)
    }
}

private val moneyKeys = setOf("cash", "equity", "available_cash", "reserved_cash", "day_pnl", "fees", "unrealized_pnl",
    "net_unrealized_pnl", "actual_debit", "cash_debit", "cash_reservation", "risk_reservation", "budget", "initial_cash", "cost")

@Composable fun DetailTree(value: JSONObject, depth: Int = 0, external: (String) -> Unit = {}) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        value.keys().asSequence().toList().forEach { key ->
            val item = value.opt(key)
            if (item is JSONObject || item is JSONArray) {
                var expanded by remember(key) { mutableStateOf(false) }
                TextButton({ expanded = !expanded }, Modifier.fillMaxWidth()) {
                    Text(friendly(key), Modifier.weight(1f), color = Ink)
                    Icon(if (expanded) Icons.Outlined.ExpandLess else Icons.Outlined.ExpandMore, null)
                }
                if (expanded) Column(Modifier.padding(start = 12.dp)) {
                    if (item is JSONObject) DetailTree(item, depth + 1, external)
                    else if (item is JSONArray) ArrayTree(item, depth + 1, external)
                }
            } else {
                val text = if (item == null || item == JSONObject.NULL) "Not available" else when (item) {
                    true -> "Yes"; false -> "No"
                    else -> if (key in moneyKeys) decimalMoney(item.toString()) else item.toString()
                }
                Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(friendly(key), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (text.startsWith("https://")) TextButton({ external(text) }) { Text("Open ${friendly(key).lowercase()} source ↗") }
                    else SelectionContainer { Text(text, style = MaterialTheme.typography.bodyMedium) }
                }
            }
        }
    }
}

@Composable fun ArrayTree(array: JSONArray, depth: Int = 0, external: (String) -> Unit = {}) {
    var limit by remember { mutableIntStateOf(20) }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (array.length() == 0) Text("No records.", style = MaterialTheme.typography.bodyMedium)
        (0 until minOf(array.length(), limit)).forEach { index ->
            val value = array.opt(index)
            when (value) {
                is JSONObject -> { DetailTree(value, depth, external); HorizontalDivider(color = Line) }
                is JSONArray -> ArrayTree(value, depth + 1, external)
                else -> Text(if (value == JSONObject.NULL) "Not available" else value.toString(), style = MaterialTheme.typography.bodyMedium)
            }
        }
        if (array.length() > limit) TextButton({ limit += 20 }) { Text("Show 20 more · ${array.length()} records total") }
    }
}
