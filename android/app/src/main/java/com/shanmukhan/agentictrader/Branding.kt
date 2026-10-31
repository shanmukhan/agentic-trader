package com.shanmukhan.agentictrader

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

@Composable internal fun BrandMark(size: Dp) {
    Surface(shape = MaterialTheme.shapes.large, color = androidx.compose.ui.graphics.Color(0xFF041A3F)) {
        Image(painterResource(R.mipmap.ic_launcher_foreground), "Agentic Trader logo", Modifier.size(size))
    }
}

@Composable internal fun WorkspaceLoadingScreen(loading: Boolean) {
    Column(Modifier.fillMaxWidth().padding(vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(18.dp)) {
        BrandMark(72.dp)
        Text("Opening your workspace", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text(if (loading) "Checking your account securely…" else "Account details could not be loaded. Use Refresh displayed status to try again.")
    }
}

@Composable internal fun EnvironmentDialog(close: () -> Unit) {
    AlertDialog(onDismissRequest = close, containerColor = MaterialTheme.colorScheme.surface, title = { Text("Trading environment") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    RadioButton(selected = true, onClick = close, modifier = Modifier.semantics { contentDescription = "Paper trading selected" })
                    Column {
                        Text("Paper · active", fontWeight = FontWeight.Bold)
                        Text("Virtual money and simulated execution. Market data may be real.")
                    }
                }
                HorizontalDivider()
                Row(verticalAlignment = Alignment.CenterVertically) {
                    RadioButton(selected = false, onClick = {}, enabled = false, modifier = Modifier.semantics { contentDescription = "Real trading unavailable" })
                    Text("Real · unavailable", fontWeight = FontWeight.Bold)
                }
                Text("Real-order execution and broker-account reconciliation are not implemented on this server. Real trading cannot be enabled yet.")
                Text("Manual, Approval and Automatic control decisions within your paper account. They do not switch to real money.", style = MaterialTheme.typography.bodySmall)
            }
        }, confirmButton = { TextButton(close) { Text("Done") } })
}
